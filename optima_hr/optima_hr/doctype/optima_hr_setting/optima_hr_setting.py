# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OptimaHRSetting(Document):
	

	@frappe.whitelist()
	def get_fields_of_salary_structure_assignment(self):

		meta = frappe.get_meta("Salary Structure Assignment", cached=False)
		return list(map(lambda x : x.get("label") , filter(lambda x : x.get("fieldtype") == "Currency" ,meta.fields) ))
