"""Bring the HR records of a site that used optima_feed's HR doctypes into the optima_hr doctypes.

Runs only when the old tables exist and have rows; a site that never had them is untouched.

In pre_model_sync on purpose: optima_feed is installed before optima_hr, so its post_model_sync
`remove_hr` patch would otherwise run first, and that patch deletes the old doctypes only after it
finds their records here.

Records are written directly, keeping docstatus, dates, owner and workflow state, and on_submit is
not run: the Additional Salary of each penalty already exists and must not be created twice. Each
target keeps the name of its source record, which is both the link back and what makes a second run
a no-op.
"""

import frappe
from frappe.core.doctype.data_import.data_import import import_doc
from frappe.utils import flt

SOURCES = ("Employee Violation", "End Of Service Request", "Letter Request", "Leave Permission")
TARGET = {
	"Employee Violation": "Employee Penalty",
	"End Of Service Request": "End of Service Benefits",
	"Letter Request": "HR Letter",
	"Leave Permission": "Permissions",
}

LABOR_LAW = "Saudi Labor Law"
OCCURRENCE = {"First": "first", "Second": "second", "Third": "third", "Fourth": "fourth"}
PERMISSION_TYPE = {"Work Assignment": "Work Assignment"}  # everything else is an Exit permission
LETTER_TEMPLATE = {
	"Salary Certificate": "Salary Certificate",
	"Experience Certificate": "Experience Letter",
	"To Whom It May Concern": "To Whom It May Concern",
	"Salary Certificate for Bank": "Salary Certificate for Bank",
}
NEW_LETTER_TEMPLATES = {
	"To Whom It May Concern": (
		"<p><strong>To Whom It May Concern</strong></p>"
		"<p>This is to certify that {{ employee_name }} is working with us as {{ designation }} "
		"since {{ joining_date }}.</p>"
		"<p>This letter is issued at the employee's request without any liability on the company.</p>"
	),
	"Salary Certificate for Bank": (
		"<p><strong>Salary Certificate</strong></p>"
		"<p>This is to certify that {{ employee_name }} is working with us as {{ designation }} "
		"since {{ joining_date }}.</p>"
		"<p>This certificate is issued at the employee's request for submission to the bank.</p>"
	),
}
NATIONALITY = {
	"Saudi Arabia": "Saudi",
	"Bangladesh": "Bangladeshi",
	"Sudan": "Sudanese",
	"Egypt": "Egyptian",
	"Pakistan": "Pakistani",
	"India": "Indian",
}
VIOLATION_TYPES = (
	"Late Arrival",
	"Absence Without Excuse",
	"Early Leave",
	"Safety Instructions Violation",
	"Work Regulations",
)
# Rows in other tables that point at a source record. Names are kept, so only the doctype changes.
DYNAMIC_LINKS = (
	("Version", "ref_doctype"),
	("Workflow Action", "reference_doctype"),
	("File", "attached_to_doctype"),
	("Comment", "reference_doctype"),
	("ToDo", "reference_type"),
	("Additional Salary", "ref_doctype"),
)


def execute():
	if not any(_has_rows(doctype) for doctype in SOURCES):
		return

	# The approved extra fields and the workflow_state columns must exist before the first insert.
	import_doc(frappe.get_app_path("optima_hr", "fixtures", "custom_field.json"))

	_copy_employee_fields()
	_ensure_masters()
	_import_violations()
	_import_end_of_service()
	_import_letters()
	_import_permissions()
	_repoint_dynamic_links()


def _has_rows(doctype):
	return frappe.db.table_exists(doctype) and frappe.db.count(doctype) > 0


def _rows(doctype):
	return frappe.get_all(doctype, fields=["*"], order_by="creation") if _has_rows(doctype) else []


def _employee(name):
	return frappe.db.get_value(
		"Employee",
		name,
		["company", "employee_number", "branch", "department", "designation", "leave_approver", "default_shift", "nationality"],
		as_dict=True,
	)


def _insert(source, doctype, values):
	if frappe.db.exists(doctype, source.name):
		return
	doc = frappe.get_doc(
		dict(
			values,
			doctype=doctype,
			name=source.name,
			docstatus=source.docstatus,
			owner=source.owner,
			creation=source.creation,
			modified=source.modified,
			modified_by=source.modified_by,
		)
	)
	doc.db_insert()


def _copy_employee_fields():
	if not frappe.db.has_column("Employee", "opf_nationality"):
		return
	employees = frappe.get_all(
		"Employee",
		filters=[["opf_nationality", "is", "set"]],
		fields=["name", "opf_nationality", "nationality", "opf_passport_no", "passport_number"],
	)
	unknown = sorted({row.opf_nationality for row in employees if row.opf_nationality not in NATIONALITY})
	if unknown:
		frappe.throw(f"No Nationality mapped for: {', '.join(unknown)}. Add them to NATIONALITY and migrate again.")

	for row in employees:
		values = {}
		if not row.nationality:
			nationality = NATIONALITY[row.opf_nationality]
			values["nationality"] = nationality
			values["is_saudi_arabia"] = frappe.db.get_value("Nationality", nationality, "is_saudi_arabia")
		if row.opf_passport_no and not row.passport_number:
			values["passport_number"] = row.opf_passport_no
		if values:
			frappe.db.set_value("Employee", row.name, values, update_modified=False)

	# Passport numbers exist on employees without a nationality too.
	frappe.db.sql(
		"""UPDATE `tabEmployee` SET passport_number = opf_passport_no
		WHERE IFNULL(opf_passport_no, '') != '' AND IFNULL(passport_number, '') = ''"""
	)


def _ensure_masters():
	if not frappe.db.exists("Labor Law", LABOR_LAW):
		frappe.get_doc({"doctype": "Labor Law", "labor_law": LABOR_LAW}).insert(ignore_permissions=True)
	for title, terms in NEW_LETTER_TEMPLATES.items():
		if not frappe.db.exists("HR Letter Template", title):
			frappe.get_doc({"doctype": "HR Letter Template", "title": title, "terms": terms}).insert(ignore_permissions=True)
	for violation_type in VIOLATION_TYPES:
		if not _penalty_type(violation_type):
			_create_penalty_type(violation_type)


def _penalty_type(violation_type):
	return frappe.db.get_value("Penalty type", {"penalty_relation": violation_type}, "name")


def _create_penalty_type(violation_type):
	rows = [row for row in _rows("Employee Violation") if row.violation_type == violation_type]
	doc = {"doctype": "Penalty type", "penalty": violation_type, "penalty_relation": violation_type}

	def usual(candidates):
		"""The most common action and deduction among the given records."""
		pairs = [(row.action, flt(row.deduction_percent) / 100) for row in candidates]
		return max(sorted(set(pairs)), key=pairs.count) if pairs else None

	overall = usual(rows) or ("Written Warning", 0)
	for occurrence, fieldname in OCCURRENCE.items():
		action, value = usual([row for row in rows if row.occurrence == occurrence]) or overall
		doc[fieldname] = action
		doc[f"{fieldname}_value"] = value
	frappe.get_doc(doc).insert(ignore_permissions=True)


def _import_violations():
	for row in _rows("Employee Violation"):
		employee = _employee(row.employee)
		_insert(
			row,
			"Employee Penalty",
			{
				"employee": row.employee,
				"company": employee.company,
				"employee_number": employee.employee_number,
				"branch": employee.branch,
				"department": row.department or employee.department,
				"designation": employee.designation,
				"posting_date": row.violation_date,
				"penalty_date": row.violation_date,
				"penalty_type": _penalty_type(row.violation_type),
				"repeat_status": OCCURRENCE.get(row.occurrence),
				"penalty": row.action,
				"penalty_value": flt(row.deduction_percent) / 100,
				"penalty_description": row.details,
				"status": "Approved" if row.docstatus == 1 else "Open",
				"deduction_percent": row.deduction_percent,
				"deduction_amount": row.deduction_amount,
				"additional_salary": row.additional_salary,
			},
		)


def _import_end_of_service():
	for row in _rows("End Of Service Request"):
		employee = _employee(row.employee)
		_insert(
			row,
			"End of Service Benefits",
			{
				"employee": row.employee,
				"designation": employee.designation,
				"company": employee.company,
				"posting_date": row.posting_date,
				"labor_law": LABOR_LAW,
				"start_work_date": row.date_of_joining,
				"end_work_date": row.last_working_day,
				"total_work_years": row.service_years,
				"request_type": row.request_type,
				"reason": row.reason,
				"gratuity": row.gratuity,
				"workflow_state": row.workflow_state,
			},
		)


def _import_letters():
	for row in _rows("Letter Request"):
		employee = _employee(row.employee)
		template = LETTER_TEMPLATE[row.letter_type]
		context = {
			"employee_name": row.employee_name,
			"designation": row.designation,
			"joining_date": row.date_of_joining,
		}
		_insert(
			row,
			"HR Letter",
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"designation": row.designation,
				"joining_date": row.date_of_joining,
				"company": employee.company,
				"nationality": employee.nationality,
				"hr_letter_template": template,
				"terms": frappe.render_template(frappe.db.get_value("HR Letter Template", template, "terms"), context),
				"directed_to": row.directed_to,
				"gross_salary": row.gross_salary,
				"posting_date": row.posting_date,
				"chamber_attestation": row.chamber_attestation,
			},
		)


def _import_permissions():
	for row in _rows("Leave Permission"):
		employee = _employee(row.employee)
		permission_type = PERMISSION_TYPE.get(row.permission_type, "Exit")
		reason = row.reason
		if permission_type == "Exit":
			# Permissions has no such types, so the original one stays readable in the reason.
			reason = f"{row.permission_type}: {row.reason}" if row.reason else row.permission_type
		_insert(
			row,
			"Permissions",
			{
				"employee_name": row.employee,
				"company": employee.company,
				"direct_manager": employee.leave_approver,
				"shift_type": employee.default_shift,
				"date": row.permission_date,
				"from_time": row.from_time,
				"to_time": row.to_time,
				"number_of_hours": row.hours,
				"reason": reason,
				"type": permission_type,
				"workflow_state": row.workflow_state,
			},
		)


def _repoint_dynamic_links():
	for source, target in TARGET.items():
		for table, column in DYNAMIC_LINKS:
			frappe.db.sql(
				f"UPDATE `tab{table}` SET `{column}` = %s WHERE `{column}` = %s",  # nosec
				(target, source),
			)
