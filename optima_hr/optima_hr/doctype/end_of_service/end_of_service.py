# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EndOfService(Document):
	pass


@frappe.whitelist()
def get_salary_structure_assignment_for_employee(employee):
	employee_assignment = frappe.db.sql(
		f"""
		SELECT *
		FROM `tabSalary Structure Assignment`
		WHERE docstatus=1 AND employee="{employee}"
		ORDER BY creation DESC
		LIMIT 1
		""", as_dict=True
	)
	if employee_assignment:
		return employee_assignment[0]
	else:
		return None