# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import date_diff 
from frappe.utils import getdate
from optima_hr.optima_hr.utils import(
    get_fields_for_leave_dues,
    get_total_amount_for_salary_structure_assignment
)

class EndofServiceBenefits(Document):

	def before_save(self):
		self.calculation()
		self.calc_salary_allowaness()
		self.calc_total_salary()
		self.calc_final_result()
	@frappe.whitelist()
	def calculation(self):
		self.days_diff()
		self.year_diff()
		

	def days_diff(self):
		self.total_work_days = date_diff(self.end_work_date , self.start_work_date)
		
	def year_diff(self):
		start_date = getdate(self.start_work_date)
		end_date = getdate(self.end_work_date)
		days_difference = abs((end_date - start_date).days)
		self.total_work_years = round((days_difference / 365.25),9)
	
	def calc_final_result(self):
		
		m1=0.5*self.total_salary
		m2=1.0*self.total_salary
		m3=0.1666667*self.total_salary
		m4=0.6666667*self.total_salary
		m5=1.0*self.total_salary

		if self.labor_law == "Article of Law 84" :
			if self.total_work_years >0 and self.total_work_years <=5:
				result = m1 * self.total_work_years
			elif self.total_work_years >5:
				result = m1 * 5 + m2 * (self.total_work_years-5)
		elif self.labor_law =="Article of Law 85" :
			if self.total_work_years < 2 :
				result = 0
			elif self.total_work_years >= 2 and self.total_work_years <= 5:
				result = m3 * self.total_work_years
			elif self.total_work_years >5 and self.total_work_years <=10:
				result = m3 * 10 + m4 * (self.total_work_years-5)				
			elif self.total_work_years >10:
				result = m3 * 5 + m4 * 10 + m5 * (self.total_work_years-10)
		else: 
			result = 0
		self.final_result = round(result,2)
	
 
	def calc_salary_allowaness(self):
		fields = get_fields_for_leave_dues(self.employee_company , "required_allowance")
		total_amount = get_total_amount_for_salary_structure_assignment(self.employee,fields)
		print(total_amount)
		self.salary_allowance = total_amount
	
	def calc_total_salary(self):
		self.total_salary = self.base_salary + self.salary_allowance
 
 	# def create_payment_entry(self):
	# 	payment_entry = frappe.new_doc("Payment Entry")

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

@frappe.whitelist()
def get_optima_hr_settings(name):
	settings = frappe.get_doc("Optima HR Setting", name)

	if settings:
		return settings

	return None