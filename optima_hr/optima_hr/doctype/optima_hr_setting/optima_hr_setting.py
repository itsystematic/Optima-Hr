# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import timedelta
from erpnext import get_default_company
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime
from hrms.hr.doctype.attendance.attendance import get_unmarked_days
from hrms.hr.doctype.shift_assignment.shift_assignment import get_shifts_for_date
from frappe.core.doctype.data_import.data_import import import_doc
import click
import os


class OptimaHRSetting(Document):
    def before_save(self) :
        if self.enable_calculate_permission_by_number == 1 :
            self.enable_add_deduction_after_permissions__hours_allowed = 0
            
        if self.enable_calculate_permission_by_hours == 1 :
            self.enable_add_deduction_after_permissions__number_allowed = 0



@frappe.whitelist()
def make_attendance_absent_for_unmarked_employee(from_date=None, to_date=None):
    
	# from_date = from_date or getdate(str(getdate() - timedelta(days=10)) ) # get custom date
    from_date = from_date or getdate().replace(day=1) # Get the first day of the current month
    to_date = to_date or getdate()

    employess = get_employees_has_unmarked_days()
    for employee in employess :
        unmarked_days = get_unmarked_days(
            employee.get("employee") ,
            from_date,
            to_date,
            1
        )

        if not unmarked_days :
            continue

        for date in unmarked_days:
            date = get_datetime(date)
            e = employee.get("employee")

            shifts = get_shifts_for_date(e, date) # fetch all shifts for given employee and date

            if shifts:
                # shift_found = False
                for shift in shifts:
                    start_date = get_datetime(shift.start_date)
                    end_date = get_datetime(shift.end_date)
                    if start_date.date() <= date.date() <= end_date.date():  # Check if date falls within shift's start and end dates
                        shift_name = shift.shift_type
                        mark_bulk_attendance({
                            "employee" : employee.get("employee") ,
                            "unmarked_days" : [date.strftime("%Y-%m-%d")],  # Convert date to string
                            "status" : "Absent",
                            "company" : get_default_company(),
                            "shift": shift_name,
                        })
            else:
                # shift type should be mandatory, otherwise raise an error
                frappe.throw(
                    msg=_(
                        "No shifts found for employee {0} on date {1}"
						).format(e, date.date()),
					title=_("No Shift Found"),
                )
            
    return frappe.msgprint(
			msg=_(
				"Attendance marked as 'Absent' for employees with unmarked days."
				),
			title=_("Attendance Marked Successfully"),
			)

def get_employees_has_unmarked_days() :
    
    return frappe.db.sql("""
        SELECT
            se.employee
        FROM `tabSet Employee Absent` se
        LEFT JOIN `tabEmployee` e
            ON e.name = se.employee
        WHERE e.status = 'Active'
        
    """,as_dict=1)
    

def mark_bulk_attendance(data):
	import json

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return

	for date in data.unmarked_days:
		doc_dict = {
			"doctype": "Attendance",
			"employee": data.employee,
			"attendance_date": get_datetime(date),
			"status": data.status,
            "shift": data.shift,  # Add this line
		}
		attendance = frappe.get_doc(doc_dict).insert()
		attendance.submit()


@frappe.whitelist()
def make_attendance(company):
	shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
	for shift in shift_list:
		doc = frappe.get_doc("Shift Type", shift)
		doc.process_auto_attendance(company)
  
  
@frappe.whitelist()
def import_doc_by_csv(name_of_doctype:str="") :
    if name_of_doctype :
        path_of_file = frappe.get_app_path("optima_hr" ,"files/" + "{}.json".format("_".join(name_of_doctype.split(" ")) ))
        import_doc(path_of_file)
        frappe.db.commit()
    
    else :
        all_files_in_folders = os.listdir( frappe.get_app_path("optima_hr" ,"files"))
        click.secho("Install Doctypes From Files  => {}".format( " ,".join(all_files_in_folders)), fg="green")
        for file in all_files_in_folders:
            import_doc(frappe.get_app_path("optima_hr" ,"files/" + f"{file}"))
            frappe.db.commit()
