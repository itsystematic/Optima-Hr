# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class SalaryEffects(Document):
    def validate(self) :
        self.validate_optima_setting()
        self.validate_mendatory_field()

    def validate_optima_setting(self):

        if not frappe.db.exists("Optima HR Setting" , {"company" : self.company}):
            frappe.throw(_("Missing Company Settings In Optima HR Setting : {0}").format(self.company))

        optima_hr_setting = frappe.db.get_value("Optima HR Setting" , self.company , ["effect_in_salary_in_journal_entry" , "effect_in_salary_in_additional_salary"] , as_dict=True)


        if optima_hr_setting.get("effect_in_salary_in_journal_entry") == 0 and optima_hr_setting.get("effect_in_salary_in_additional_salary") == 0 :
            frappe.throw(_("You Must Choose Way To Make Effect In Salary"))



    def validate_employee_salary_structure(self) :
        """
        Validate that all employees have a valid salary structure assignment
        :raises frappe.exceptions.ValidationError: if no salary structure assignment is found
        """

        for row in self.employees_component :
            if not frappe.db.exists("Salary Structure Assignment" , {"employee" : row.employee_id , "docstatus" : 1}):
                frappe.throw("Please Assign Employee To Salary Structure And Sift")

    def validate_mendatory_field(self) :
        if len(self.employees_component) < 1 :
            frappe.throw("Please Add Employee Component")

    def on_submit(self):
        self.validate_employee_salary_structure()
        self.make_effects_to_employee()


    def make_effects_to_employee(self) :

        optima_hr_setting = frappe.db.get_value("Optima HR Setting" , self.company , ["effect_in_salary_in_journal_entry" , "effect_in_salary_in_additional_salary" , "credit_account_in_journal_entry"] , as_dict=True)

        if optima_hr_setting.get("effect_in_salary_in_journal_entry") == 1 :
            credit_account = optima_hr_setting.get("credit_account_in_journal_entry")
            self.create_journal_entry(credit_account)

        if optima_hr_setting.get("effect_in_salary_in_additional_salary") == 1 :
            self.create_additional_salary()


    def create_journal_entry(self,credit_account):
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.user_remark = "Salary Effect : {0}".format(self.name)
        journal_entry.company = self.company
        journal_entry.posting_date = self.date

        for row in self.employees_component :
            debit_account = get_salary_component_account(self.company , row.procedure)
            
            if not debit_account :
                frappe.throw(_("Please Set Account In Salary Component {0} To Company {1}").format(row.procedure , self.company))

            journal_entry.append("accounts",{
                "account" : debit_account,
                "debit" : row.amount,
                "debit_in_account_currency" : row.amount,
                "party_type" : "Employee",
                "party" : row.employee_id
            })

            journal_entry.append("accounts",{
                "account" : credit_account,
                "credit" : row.amount,
                "credit_in_account_currency" : row.amount,
                "party_type" : "Employee",
                "party" : row.employee_id
            })
            print(row.amount)
        journal_entry.save()
        journal_entry.submit()


    def create_additional_salary(self):
        for row in self.employees_component:
            doc  =  frappe.get_doc({
                "doctype" : "Additional Salary",
                "employee" : row.employee_id ,
                "amount" : row.amount ,
                "payroll_date" : self.date ,
                "salary_component" : row.procedure,
                "custom_project" : row.project,
                "overwrite_salary_structure_amount" : 0,
                "ref_doctype" : self.doctype,
                "ref_docname" : self.name,
                "custom_remarks" : row.remarks or None,
            })
            doc.submit()

    def on_cancel(self) :
        self.ignore_linked_doctype = "Additional Salary"
        self.cancel_doctype_link()

    def cancel_doctype_link(self) :
        
        #for additional_salary in self.additional_salary_id :
            
            #doc = frappe.get_doc("Additional Salary" , additional_salary)
            #doc.cancel()
        pass

    @frappe.whitelist()
    def get_percent_hour(self,employee,component,qty):
        result = 0

        hours , absent , percent = frappe.db.get_value("Salary Component" , {"salary_component" : component }, ["hours" , "absent" , "percent"])
        employee_base_amount = self.get_employee_base_amount(employee)

        if hours == 1 :
        
            shift_hours = self.get_shift_hours(self.get_employee_shift(employee))
            hour_price= self.get_hour_price(employee_base_amount,shift_hours)
            result = hour_price * qty * percent
        
        if absent == 1 :
            
            day_price= self.get_day_price(employee_base_amount)   
            result = day_price*percent*qty

        return result
                    

    def get_employee_base_amount(self,employee):
        componants=frappe.db.get_all("Salary Component" , {"is_account_total_in_salary_effect" : 1} , "ssa_name")
        total_salary=0
        for componant in componants :
            total_salary  += frappe.db.get_value("Salary Structure Assignment" , {"employee" : employee , "docstatus" : 1},componant.get("ssa_name"))
        return total_salary
            
        
    def get_employee_shift(self,employee):
            employee_shift = frappe.db.get_value("Shift Assignment" , {"employee" : employee , "docstatus" : 1}, "shift_type")
            if not employee_shift:
                employee_shift = frappe.db.get_value("Employee" , {"name" : employee} , "default_shift")
            return employee_shift
        
    def get_shift_hours(self,employee_shift):
            
        shift_duration = get_shift_propertise(self.company , employee_shift )

        return shift_duration
        #     pass

        # else :
        #     start_time , end_time =frappe.db.get_value("Shift Type" , {"name" : employee_shift} , ["start_time" , "end_time"])
        #     shift_hours = (end_time - start_time).total_seconds() / 3600
        #     return shift_hours
        
    def get_hour_price(self,employee_base_amount,shift_hours):
        hour_price = (employee_base_amount/30) / shift_hours
        return hour_price
        
    def get_day_price(self,employee_base_amount):
        day_price = (employee_base_amount/30)
        return day_price

def get_shift_propertise(company , shift_type) :
    shift_duration = None
    if settings := frappe.db.exists("Optima HR Setting" , {"company" : company}):
        hr_settings = frappe.get_doc("Optima HR Setting" , settings)

        if hr_settings.enable_shift_duration :
            row = next(filter(lambda x : x.get("shift_type") == shift_type , hr_settings.enable_shift_types))
            shift_duration = row.get("shift_duration")

    if not shift_duration :
        start_time , end_time = frappe.db.get_value("Shift Type" , {"name" : shift_type } , ["start_time" , "end_time"])
        shift_duration = ( end_time - start_time ).total_seconds() / 3600

    return shift_duration




def get_salary_component_account(company ,component):

    return frappe.db.get_value("Salary Component Account" , {"company" : company ,"parent" : component} , "account")