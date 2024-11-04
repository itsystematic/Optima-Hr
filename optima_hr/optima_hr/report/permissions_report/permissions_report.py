# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(filters: dict) -> list[dict]:

	permissions_data = frappe.db.sql("""
    SELECT 
		p.date,
		p.employee_name,
		p.type,
		e.reports_to AS manger,
		p.from_time,
		p.to_time
    FROM 
        `tabPermissions` p
	LEFT JOIN
		`tabEmployee` e
		ON
			e.name = p.employee_name
	WHERE 1=1
		{conditions}
	""".format(conditions=get_conditions(filters)),
		as_dict=True)

	return permissions_data

def	 get_columns(filters: dict) -> list[dict]:
	columns = [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Manger"),
			"fieldname": "manger",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},
		{
			"fieldname": "from_time",
			"label": _("From Time"),
			"fieldtype": "Time",
			"reqd": 1,
			"width": 150,
		},
		{
			"fieldname": "to_time",
			"label": _("To Time"),
			"fieldtype": "Time",
			"reqd": 1,
			"width": 150,
		},
	]

	return columns

def get_conditions(filters: dict) -> str:

	Condition = ""

	if filters.get("from_time") and filters.get("to_time"):
		Condition += f" AND p.from_time >= '{filters.get('from_time')}' AND p.to_time <= '{filters.get('to_time')}' "

	if filters.get("date"):
		Condition += f" AND p.date = '{filters.get('date')}' "

	if filters.get("employee_name"):
		Condition += f" AND p.employee_name = '{filters.get('employee_name')}' "

	if filters.get("type"):
		Condition += f" AND p.type = '{filters.get('type')}' "

	return Condition