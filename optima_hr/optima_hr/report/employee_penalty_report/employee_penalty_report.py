# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters: dict) -> list[dict]:
	columns = [
		{
			"fieldname": "penalty",
			"label": _("Penalty"),
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 200,
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},
		{
			"fieldname": "penalty_type",
			"label": _("Penalty Type"),
			"fieldtype": "Link",
			"options": "Penalty Type",
			"width": 200,
		},
		{
			"fieldname": "repeat_status",
			"label": _("Repeat Status"),
			"fieldtype": "Select",
			"options": "first\nsecond\nthird\nfourth",
			"width": 200,
		},
		{
			"fieldname": "penalty_description",
			"label": _("Penalty Description"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{
			"fieldname": "subject", 
			"label": _("Subject"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Select",
			"options": "Open\nApproved\nRejected",
			"width": 200,
		}
		
	]

	return columns

def get_data(filters: dict) -> list[dict]:
	penalty_data = frappe.db.sql(
		"""
			SELECT
				employee,
				penalty,
				posting_date,
				penalty_type,
				repeat_status,
				penalty_description,
				subject,
				status

			FROM
				`tabEmployee Penalty`
			WHERE 1=1
			{conditions}
		""".format(conditions=get_conditions(filters))
			, as_dict = True
	)

	return penalty_data

def get_conditions(filters: dict) -> str:
	conditions = ""
	
	if filters.get("employee"):
		conditions += f" AND employee = '{filters.get('employee')}'"
	
	if filters.get("company"):
		conditions += f" AND company = '{filters.get('company')}'"
	
	if filters.get("penalty"):
		conditions += f" AND penalty = '{filters.get('penalty')}'"

	if filters.get("penalty_type"):
		conditions += f" AND penalty_type = '{filters.get('penalty_type')}'"

	if filters.get("repeat_status"):
		conditions += f" AND repeat_status = '{filters.get('repeat_status')}'"

	if filters.get("status"):
		conditions += f" AND status = '{filters.get('status')}'"

	if filters.get("from_date") and filters.get("to_date"):
		conditions += f" AND posting_date BETWEEN '{filters.get('from_date')}' AND '{filters.get('to_date')}'"

	
	return conditions