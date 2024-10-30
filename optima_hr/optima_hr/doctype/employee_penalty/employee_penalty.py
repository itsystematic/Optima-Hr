# Copyright (c) 2023, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate , add_months
from frappe.model.document import Document
from optima_hr.optima_hr.utils import create_additional_salary , get_employee_salary



PENALITY_NUMBER = {
    '0' : "first" ,
    '1' : "second" ,
    '2' : "third" ,
    '3' : "fourth" ,
}

class EmployeePenalty(Document):
    
    def validate(self):
        self.validate_company_settings()
        self.check_employee_has_salary_structure_asignment()
        
    def validate_company_settings(self):

        if not frappe.db.exists("Optima HR Setting",self.company) :
            frappe.throw(_("Missing Company Settings In Optima HR Setting : {0}").format(self.company))

        company_settings = frappe.get_doc("Optima HR Setting",self.company)
        company_settings_fields = ["default_salary_component_for_employee_penalty" , "penalty_component"]
        
        for field in company_settings_fields :
            if not company_settings.get(field) :
                frappe.throw(_("Please Set {0} In Optima HR Setting").format(field.replace("_"," ").title()))

    
    def check_employee_has_salary_structure_asignment(self):
        if not frappe.get_list("Salary Structure Assignment",{"employee" : self.employee , "docstatus" : 1} , pluck='name') :
            frappe.throw(_("Employee Not have Salary Structure Assignment"))
        
        
    @frappe.whitelist()
    def get_employee_penallty_repeat_state_and_penalty(self):
        self.get_penality_number_for_employee()
        self.get_penalty()


    def get_penality_number_for_employee(self):
        if self.employee and self.penalty_type :
            begining_date = get_payroll_date_beginning_for_this_month(self.company , self.penalty_date)
            employee_penalty_number = frappe.db.count('Employee Penalty',{
                'docstatus': 1 ,
                "employee" : self.employee , 
                "penalty_type" : self.penalty_type ,
                'penalty_date': ['between', [begining_date , add_months(begining_date , 1)] ] ,
            })
            self.repeat_status = PENALITY_NUMBER.get(f'{employee_penalty_number}' , "fourth")


    def get_penalty(self):
        self.penalty , self.penalty_value =  frappe.db.get_value("Penalty type" , {"name" : self.penalty_type} , [self.repeat_status , self.repeat_status + '_value' ])


    def on_submit(self):
        self.check_approved_status()
        self.create_additional_salary()


    def check_approved_status(self):
        if self.status != 'Approved' :
            frappe.throw(_("Status Must be Approved"))


    def create_additional_salary(self):
        employee_base_amount  = get_employee_salary(self.employee , "penalty_component") 
        salary_component = frappe.db.get_value("Optima HR Setting" , self.company , "default_salary_component_for_employee_penalty")
        if self.penalty_value > 0  and self.status == 'Approved' : 
            amount = (employee_base_amount / 30) * ( self.penalty_value or 1 ) 
            
            doc = create_additional_salary(
                employee=self.employee,
                posting_date=self.posting_date,
                amount=amount ,
                salary_component= salary_component,
                ref_doctype=self.doctype,
                ref_docname=self.name
                )
            
            
    def on_cancel(self):
        self.cancel_doctype_link()
        
    def cancel_doctype_link(self):
        if frappe.db.exists("Additional Salary" , {"ref_doctype" : self.doctype , "ref_docname" : self.name}) :
            additional_salary = frappe.get_doc("Additional Salary" , {"ref_doctype" : self.doctype , "ref_docname" : self.name})
            additional_salary.cancel()



def get_payroll_date_beginning_for_this_month(company, penalty_date):

    payroll_date_beginning = frappe.db.get_value("Optima HR Setting", {"company": company}, "payroll_date_beginning")
    converted_penalty_date = getdate(penalty_date)

    return getdate(payroll_date_beginning).replace(month=converted_penalty_date.month , year=converted_penalty_date.year)