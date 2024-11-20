# Copyright (c) 2024, IT Systematic Company and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEndofServiceBenefits(FrappeTestCase):
	def test_final_result_set__auto(self):
		test_benefits = frappe.new_doc("End of Service Benefits")
		test_benefits.employee = "HR-EMP-00001"
		test_benefits.end_work_date = "2024-11-18"
		test_benefits.labor_law = "Article of Law 84"
		test_benefits.insert()

		self.assertEqual(test_benefits.final_result, 2047.91)
	
	
	def test_final_result_set__auto_2(self):
		test_benefits = frappe.new_doc("End of Service Benefits")
		test_benefits.employee = "HR-EMP-00001"
		test_benefits.end_work_date = "2024-11-18"
		test_benefits.labor_law = "Article of Law 84"
		test_benefits.save()

		self.assertEqual(test_benefits.final_result, 21999)