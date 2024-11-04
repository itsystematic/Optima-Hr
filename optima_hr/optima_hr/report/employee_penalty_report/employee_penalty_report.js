// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Penalty Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
		},
		{
			"fieldname": "penalty",
			"label": __("Penalty"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "penalty_type",
			"label": __("Penalty Type"),
			"fieldtype": "Link",
			"options": "Penalty type",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": ["", "Open", "Approved", "Rejected"],
		},
		{
			"fieldname": "repeat_status",
			"label": __("Repeat Status"),
			"fieldtype": "Select",
			"options": ["", "first", "second", "third", "fourth"],
		}
	]
};
