# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OptimaHRSetting(Document):
	


	@frappe.whitelist()
	def get_fields_of_salary_structure_assignment(self):

		return frappe.get_all("DocField" , {
			"parent" : "Salary Structure Assignment" ,
			"fieldtype" : "Currency" 
			} , 
			pluck="label" ,
			order_by="idx"
		)