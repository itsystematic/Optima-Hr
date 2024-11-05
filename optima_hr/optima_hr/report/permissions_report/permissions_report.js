// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.query_reports["Permissions Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
		},
		{
			"fieldname": "employee_name",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
		},
		{
			"label": __("From Time"),
			"fieldname": "from_time",
			"fieldtype": "Time",
			// "reqd": 1
		},
		{
			"label": __("To Time"),
			"fieldname": "to_time",
			"fieldtype": "Time",
			// "reqd": 1
		},
		{
			"fieldname": "type",
			"label": __("Type"),
			"fieldtype": "Select",
			"options": ["Exit", "Enter", "Work Assignment"],
			"default": "Exit",
		},
	]
};
