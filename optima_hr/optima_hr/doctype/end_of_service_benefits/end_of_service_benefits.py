# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.data import date_diff 
from frappe.utils import getdate ,flt
from frappe.query_builder.functions import Sum
from optima_hr.optima_hr.utils import get_closing_balances
class EndofServiceBenefits(Document):

    def before_save(self):
        self.calculation()
        self.calc_total_salary()
        self.calc_final_result_with_additional()
        self.get_closing_balances()
        
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
        return  round(result,2)
    
    def calc_total_salary(self):
        self.total_salary = self.base_salary + self.salary_allowance
    
    def calc_final_result_with_additional(self):
        final_res = self.calc_final_result()
        if self.is_last_work_days_salary:
            final_res = final_res + self.last_work_days_salary
        if self.is_travel_cost ==1 and self.ticket_cost > 0:
            final_res = final_res + self.ticket_cost
        if self.employee_advance:
            final_res = final_res + self.closing_cr - self.closing_de
        if self.outstanding_leaves:
            final_res = final_res + self.outstanding_leave_balance_amount
        self.final_result =final_res
    
    def get_closing_balances(self):
        closing_balance = get_closing_balances(self.company, self.end_work_date, self.employee)
        self.closing_cr = closing_balance.get("closing_credit")
        self.closing_de = closing_balance.get("closing_debit")
        
    def set_total_advance_paid(self) :
        gle = frappe.qb.DocType("GL Entry")

        paid_amount = (
            frappe.qb.from_(gle)
            .select(Sum(gle.debit).as_("paid_amount"))
            .where(
                (gle.against_voucher_type == self.doctype)
                & (gle.against_voucher == self.name)
                & (gle.party_type == "Employee")
                & (gle.party == self.employee)
                & (gle.docstatus == 1)
                & (gle.is_cancelled == 0)
            )
        ).run(as_dict=True)[0].paid_amount or 0

        if paid_amount > flt(self.final_result):
            frappe.throw(
                _("Row {0}# Paid Amount cannot be greater than Final Result"),
            )
        self.db_set("paid_amount", paid_amount)



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