# Copyright (c) 2023, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from optima_hr.optima_hr.utils import create_additional_salary
from frappe.utils import get_first_day , time_diff ,get_datetime
import datetime

class Permissions(Document):
    
        
    def __init__(self, *args, **kwargs):
        super(Permissions, self).__init__(*args, **kwargs)
        self.set_time_difference()
        

    def onload(self):
        self.get_settings()
    
    def get_settings(self):
         setting = frappe.get_doc("Optima HR Setting",self.company)
         self.allowed_hour = setting.allowed_permission_hours
         print(self.allowed_hour)
         print(setting.allowed_permission_hours)
         print(setting.get("enable_calculate_permission_by_hours"))
         return setting
    def validate(self):
        print(self.get_settings().allowed_permission_hours)
        self.validate_difference_time_calculation()      
        self.validate_allowed_hours()
        self.validate_company_salary_component()
        self.vaildate_employee_daily_permission()
        self.validate_number_of_permission_hours_allowed()
        self.validate_number_of_permission_number_allowed()



    def validate_difference_time_calculation(self):
        if self.from_time > self.to_time :
            frappe.throw(_("To Time Must be Greater Than From Time"))     
            
            
    def validate_allowed_hours(self):
        if self.type == "Exit" and self.time_difference > self.allowed_hour and self.get_settings().get("enable_calculate_permission_by_hours") and self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0:
            frappe.throw(_("The Maximum Permission Hours {0}".format(self.get_settings().allowed_permission_hours)))
            
            
    def validate_company_salary_component(self):
        if self.type == "Exit" and not self.get_settings().get("default_salary_component_for_permissions" , None) and (self.get_settings().enable_add_deduction_after_permissions__number_allowed == 1 or self.get_settings().enable_add_deduction_after_permissions__hours_allowed == 1) :
            frappe.throw(_("Salary Component in Setting is required"))

            
    def vaildate_employee_daily_permission(self):
        if frappe.db.exists("Permissions", {"date" : self.date , "employee_name" : self.employee_name , "docstatus" : 1 , 'type' : "Exit"}, cache=True):
            frappe.throw(_("Employee Must Have 1 Permission Per Day"))
    
    
    def validate_number_of_permission_hours_allowed(self):
        
        if self.type == "Exit" and self.get_settings().get("enable_calculate_permission_by_hours") and self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0 :
            number_of_hours = self.get_total_hours_taken()
            
            if number_of_hours + self.time_difference > self.allowed_hour :
                frappe.throw(_("The Maximum Working Hours have been Exhausted {0}".format(self.get_settings().allowed_permission_hours)))


    def validate_number_of_permission_number_allowed(self):
        payroll_date_beginning = self.get_settings().get("payroll_date_beginning")
        if self.get_settings().get("enable_calculate_permission_by_number") and self.get_settings().get("enable_add_deduction_after_permissions__number_allowed") == 0 and self.type == "Exit":        
            
            filters = {
                'date': ['>=',payroll_date_beginning] ,
                'docstatus' : 1 ,
                'employee_name' : self.employee_name ,
                'type' : "Exit"
            }
            number_of_permission = frappe.db.get_list('Permissions', filters=filters,  fields=["COUNT(name) as name"])
            
            if number_of_permission[0].get("name") != None:
            
                if number_of_permission[0].get("name")  >  self.get_settings().allowed_permission_numbers :
                    frappe.throw(_("The Maximum Permsission Available {0}".format(self.get_settings().allowed_permission_numbers)))
    
    @frappe.whitelist()
    def set_time_difference(self):
        if self.from_time and self.to_time:
            self.time_difference = time_diff( self.to_time , self.from_time)


    def before_submit(self):
        self.add_deduction_after_permission_hours_allowed()
        self.add_deduction_after_permission_number_allowed()



    def add_deduction_after_permission_hours_allowed(self):
        if self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") and self.type == "Exit":
            pass
        
        
    
    def add_deduction_after_permission_number_allowed(self):
        if self.get_settings().get("enable_add_deduction_after_permissions__number_allowed")  and self.type == "Exit":
            per = frappe.db.count('Permissions', {"docstatus": 1  , "employee_name" : self.employee_name , 'type' : "Exit"})
            if (per + 1 ) > self.get_settings().get("allowed_permission_numbers") :
                self.create_additional_salary()

    
    def create_additional_salary(self):
        salary = frappe.get_last_doc('Salary Structure Assignment', filters={"employee" : self.employee_name}, order_by="creation desc")

        if not salary.get("base" , None) :
            frappe.throw(_("Base is required in Salary Structure Assignment"))
        

        create_additional_salary(
            employee=self.employee_name,
            posting_date=self.date,
            amount=100 ,
            salary_component=self.get_settings().get("default_salary_component_for_permissions"),
            ref_doctype=self.doctype,
            ref_docname=self.name
        )
        # self.additional_salary_name = doc.name
        
        
    def on_cancel(self):
        self.cancel_additional_salary_if_exists()


    def cancel_additional_salary_if_exists(self):
        # if self.additional_salary_name :
        if frappe.db.exists("Additional Salary" , {"ref_doctype" : self.doctype , "ref_docname" : self.name}) :
            additional_salary = frappe.get_doc("Additional Salary" , {"ref_doctype" : self.doctype , "ref_docname" : self.name})
            additional_salary.cancel()
        
    
    @frappe.whitelist()
    def get_total_time_remaining(self):
        print('get_total_time_remaining')
        if self.allowed_hour and self.get_settings().get("enable_calculate_permission_by_hours") :
            print('get_total_time_remaining 01 ')
            all_times_for_employee = self.get_total_hours_taken()
            print(all_times_for_employee)
            total_delta =  self.allowed_hour - all_times_for_employee
            print(total_delta)

            return total_delta
    
    
    def get_total_hours_taken(self):
        filters = {
            'date': ['>=',get_first_day(self.date) ] ,
            'docstatus' : 1 ,
            'employee_name' : self.employee_name ,
            'type' : "Exit" ,
            "time_difference" : ["is", "set"] 
        }
        
        all_times_for_employee = frappe.db.get_list("Permissions" , filters, pluck="time_difference")
        
        return sum(all_times_for_employee, datetime.timedelta()) 
    
    
    