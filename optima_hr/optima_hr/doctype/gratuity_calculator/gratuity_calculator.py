# Copyright (c) 2023, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import date_diff 
import math
import erpnext
from frappe import _
class GratuityCalculator(Document):

    def before_save(self):
        self.set_default_company()
        self.calculation()
        self.null_fields()

    def set_default_company(self) :
        if not self.company:
            self.company = erpnext.get_default_company()

    def null_fields(self):
        if self.gratuity_type != "Resignation" :
            self.description = ""
            self.labor_law = ""

    @frappe.whitelist()
    def calculation(self):
        self.days_diff()
        self.year_diff()
        self.sum_total_salary()
        self.clac_working_days_amount()
        self.calc_leave_encashment_amount()
        self.calc_return_paid_leave_days()
        self.net_total_gratuity_amount()

    def days_diff(self):
        self.total_work_days = date_diff(self.end_work_date , self.start_work_date)
        
    def year_diff(self):
        self.total_work_years = math.floor(date_diff(self.end_work_date , self.start_work_date) / 365)

    def sum_total_salary(self):
        self.total_salary = round((self.last_salary_slab_amount or 0 ) + (self.salary_allowance or 0 ), 2)

    def clac_working_days_amount(self):
        self.last_working_days_salary = round(((self.total_salary or 0) / 30 ) * (self.last_working_days or 0), 2 )

    def calc_leave_encashment_amount(self):
        self.leave_encashment_amount = round(((self.total_salary or 0) / 30 ) * (self.leave_encashment_days or 0), 2)

    def calc_return_paid_leave_days(self):
        self.return_paid_leave_amount =  round(-((self.total_salary or 0) / 30 ) * (self.return_paid_leave_days or 0), 2)

    def net_total_gratuity_amount(self):
        if self.gratuity_type == "Resignation" :
            
            if self.labor_law == "Article of Law 84" :
                
                result  = self.low_eighty_four()
                
            elif self.labor_law =="Article of Law 85" :
                
                result_low_eighty_four = self.low_eighty_four()
                result = self.low_eighty_five(result_low_eighty_four) 
                
            else :
                result = 0
                
            self.total_gratuity_amount = round(result + ((self.fly_ticket or 0) + self.last_working_days_salary + self.leave_encashment_amount ) - (abs(self.return_paid_leave_amount) + ( self.return_loans or 0 ) ) , 2)
        
        else :
            self.total_gratuity_amount = round(((self.fly_ticket or 0) + self.last_working_days_salary + self.leave_encashment_amount ) - (abs(self.return_paid_leave_amount) + ( self.return_loans or 0 ) ),2)


    def low_eighty_four(self):
        total = 0
        if self.total_work_days >= 365  and self.total_work_days < 1825 :
            total += ( ( self.total_salary * ( 50 / 100) ) / 365 ) * (self.total_work_days + 1)

        elif self.total_work_days >= 1825 :
            days_after_five_year = self.total_work_days - 1825
            total += ( ( self.total_salary * ( 50 / 100) ) / 365 ) * (self.total_work_days - days_after_five_year)
            total +=  ( self.total_salary / 365 ) * days_after_five_year
        return total
    
    def low_eighty_five(self ,Amount):
        total = 0
        if self.total_work_days < 730 :
            total = 0 
        elif self.total_work_days >= 730  and self.total_work_days < 1825 :
            total = Amount / 3
        elif self.total_work_days >= 1825  and self.total_work_days < 3650 :
            total = Amount * 0.6666
        elif self.total_work_days >= 3650: 
            total = Amount

        return total
    
    
    def on_submit(self) :
        self.check_of_fields_before_submit()
        self.create_journal_entry()


    
    def check_of_fields_before_submit(self) :
        hr_setting = frappe.get_doc("HR Permission Settings")
        fields = ["leave_and_resignation_payment_account" , "resignation_account" , "leave_account"]
        for field in fields :
            if hr_setting.get(field) == None :
                frappe.throw(_("This Field {} is Missing in Settings".format(" ".join(field.split("_")))))

    def create_journal_entry(self , *args,**kwargs):
        hr_setting = frappe.get_doc("HR Permission Settings")
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.user_remark = " " 
        journal_entry.company = self.company
        journal_entry.posting_date = self.posting_date
        employee_cost_center = frappe.get_doc("Employee" , self.employee).get("payroll_cost_center") or ""

        if self.gratuity_type == "Resignation" :
            journal_entry.append("accounts", {
                'account' : hr_setting.get("resignation_account") ,"party" : self.employee , "party_type" : "Employee","cost_center" : employee_cost_center , "debit" : self.total_gratuity_amount , "debit_in_account_currency" :self.total_gratuity_amount  , "credit" : 0.00 , "credit_in_account_currency" :0.00
            })
            
        else :
            journal_entry.append("accounts", {
                'account' : hr_setting.get("leave_account") ,"party" : self.employee , "party_type" : "Employee","cost_center" : employee_cost_center , "debit" : self.total_gratuity_amount , "debit_in_account_currency" :self.total_gratuity_amount  , "credit" : 0.00 , "credit_in_account_currency" :0.00
            })

        journal_entry.append("accounts", {
            'account' : hr_setting.get("leave_and_resignation_payment_account"), "cost_center" : employee_cost_center ,"debit" : 0.00 , "debit_in_account_currency" : 0.00 , "credit" : self.total_gratuity_amount  , "credit_in_account_currency" :self.total_gratuity_amount 
        })            
        journal_entry.save(ignore_permissions=True)
        
        self.reference_name = journal_entry.name
        
        # journal_entry.save(ignore_permissions=True)


@frappe.whitelist()
def get_employee_details(employee:str= "" , gratuity_type:str=""):
    result = {}
    get_last_salary(employee , result)
    get_employee_date_of_joining_or_start_work_date(employee ,gratuity_type, result)
    # get_employee_return_loans(employee , result)
    get_salary_allowance(employee, result)
    return result
    


def get_employee_date_of_joining_or_start_work_date(employee:str="" , gratuity_type:str="", result:dict={}):
    employee_details = frappe.get_doc("Employee" , employee)
    if gratuity_type == "Resignation" :
        start_work_date = employee_details.get("date_of_joining", "")
    else :
        start_work_date =  employee_details.start_work_date if employee_details.get("start_work_date") else employee_details.get("date_of_joining", "")
    result.update({
        "start_work_date" :start_work_date
    })


def get_employee_return_loans(employee:str="" , result:dict={}):
    employee_leans = frappe.db.get_all("GL Entry",filters= { "party" : employee , "is_cancelled" : 0}, fields = ['SUM(debit) as total_debit' , 'SUM(credit) as total_credit' ], group_by='party')
    
    result.update(
        # {"return_loans" : employee_leans[0].get("total_debit" , 0) - employee_leans[0].get("total_credit" , 0)} if employee_leans else {"return_loans": 0}
        {"return_loans" : employee_leans[0].get("total_debit" , 0) - employee_leans[0].get("total_credit" , 0) if employee_leans else 0 } 
    )


def get_last_salary(employee:str = "" , result:dict={}):
    last_salary_slab_amount = get_employee_base_amount(employee)
    result.update({
        "last_salary_slab_amount" : last_salary_slab_amount
    })


def get_salary_allowance(employee, result) -> None:
    return_data = frappe.db.sql(f"""
                SELECT  variable + custom_home_allowance + custom_other + custom_bouns + custom_transportation_allowance + custom_mobile_allowance AS salary_allowance
                FROM `tabSalary Structure Assignment`
                WHERE docstatus=1 AND employee="{employee}"
                ORDER BY creation DESC
                LIMIT 1;
        """, as_dict=True)
    #-- change fields name to custom_ and calculate salary allowance --
    
    # return_data = frappe.db.sql(f"""
    #             SELECT custom_home_allowance AS salary_allowance
    #             FROM `tabSalary Structure Assignment`
    #             WHERE docstatus=1 AND employee="{employee}"
    #             ORDER BY creation DESC
    #             LIMIT 1;
    #     """, as_dict=True)   
    
    result.update(return_data[0] if return_data else {"salary_allowance": 0})

@frappe.whitelist()
def make_payment_entry(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_type = "Pay"
		target.party_type="Employee"
		target.party=source.employee
        

	doclist = get_mapped_doc(
		"Gratuity Calculator",
		source_name,
		{
			"Gratuity Calculator": {
			"doctype": "Payment Entry",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist