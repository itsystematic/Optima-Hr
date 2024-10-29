# Copyright (c) 2023, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from optima_hr.optima_hr.utils import create_additional_salary
from frappe.utils import get_first_day , time_diff ,get_datetime ,getdate , today
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
         return setting
     
    def validate(self):
        self.validate_difference_time_calculation()              
        self.validate_allowed_hours()
        self.validate_company_salary_component()        
        self.vaildate_employee_daily_permission()        
        self.validate_number_of_permission_hours_allowed()                
        self.validate_number_of_permission_number_allowed()
        if self.type != "Exit":
            self.extra_hours = None
            self.remaining_hours = None




    def validate_difference_time_calculation(self):
        if self.from_time > self.to_time :
            frappe.throw(_("To Time Must be Greater Than From Time"))
    
    def validate_remaining_hours(self):
        if self.type == "Exit" and self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0:
            if self.time_difference > self.get_total_time_remaining():
                frappe.throw(_("The Maximum Working Hours have been Exhausted {0}".format(self.get_settings().allowed_permission_hours)))

    def validate_allowed_hours(self):
        if self.type == "Exit":
            if self.time_difference > self.get_total_time_remaining():
                if  self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0:
                    frappe.throw(_("The Maximum Permission Hours {0}".format(self.get_settings().allowed_permission_hours))) 
            
            
    def validate_company_salary_component(self):
        if self.type == "Exit" and not self.get_settings().get("default_salary_component_for_permissions" , None) and (self.get_settings().enable_add_deduction_after_permissions__number_allowed == 1 or self.get_settings().enable_add_deduction_after_permissions__hours_allowed == 1) :
            frappe.throw(_("Salary Component in Setting is required"))

            
    def vaildate_employee_daily_permission(self):
        # if frappe.db.exists("Permissions", {"date" : self.date , "employee_name" : self.employee_name , "docstatus" : 1 , 'type' : "Exit"}, cache=True):
        if self.type =="Exit":
            filters = {
            'date': ['>=',self.get_payroll_date_beginning_for_this_month()] ,
            'docstatus' : 1 ,
            'employee_name' : self.employee_name ,
            'type' : "Exit"
            }
            number_of_permission = frappe.db.get_list('Permissions', filters=filters,  fields=["COUNT(name) as name"])
            
            if number_of_permission[0].get("name")> self.get_settings().get("default_permissions_per_day") :
                frappe.throw(_(f"Employee Must Have {self.get_settings().default_permissions_per_day} Permission Per Day"))
    
    
    def validate_number_of_permission_hours_allowed(self):
        
        if self.type == "Exit" and self.get_settings().get("enable_calculate_permission_by_hours") and self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0 :
            number_of_hours = self.get_total_hours_taken()
            
            if number_of_hours + self.time_difference > self.allowed_hour :
                frappe.throw(_("The Maximum Working Hours have been Exhausted {0}".format(self.get_settings().allowed_permission_hours)))


    def validate_number_of_permission_number_allowed(self):
        if self.type == "Exit":
            payroll_date_beginning = self.get_payroll_date_beginning_for_this_month()
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
        self.extra_hours = None
        if self.allowed_hour and self.get_settings().get("enable_calculate_permission_by_hours") == 1:    
            all_times_for_employee = self.get_total_hours_taken()   
            total_delta =  self.allowed_hour - all_times_for_employee    
            if self.type == "Exit" :
                if self.time_difference > total_delta:
                    if self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0:
                        frappe.throw(_("The Maximum Working Hours have been Exhausted {0}".format(self.get_settings().allowed_permission_hours)))
                    elif self.time_difference < total_delta:
                        self.remaining_hours = self.time_difference - total_delta
                    if total_delta != None:
                        self.extra_hours = self.time_difference - total_delta
                        self.remaining_hours = None
                    elif total_delta == None:
                        self.remaining_hours = None
                        self.extra_hours = self.time_difference
                else:
                    self.remaining_hours = total_delta -self.time_difference 
                    self.extra_hours = None
                    
            else:
                self.remaining_hours = total_delta
                self.extra_hours = None
            return total_delta

    # @frappe.whitelist()
    # def get_total_time_remaining(self):
    #     if self.allowed_hour and self.get_settings().get("enable_calculate_permission_by_hours"):            
    #         all_times_for_employee = self.get_total_hours_taken()            
    #         total_delta = self.allowed_hour - all_times_for_employee     
            
    #         if self.type == "Exit" and self.remaining_hours is not None:
    #             # Convert time differences to seconds for calculation
    #             total_delta_seconds = total_delta.total_seconds()
    #             time_diff_seconds = self.time_difference.total_seconds()
    #             remaining_seconds = total_delta_seconds - time_diff_seconds
    #             # Convert back to timedelta, but ensure it's not negative
    #             from datetime import timedelta
    #             self.remaining_hours = timedelta(seconds=max(0, remaining_seconds))
    #         else:
    #             self.remaining_hours = total_delta
                
    #         return total_delta    
    
    def get_total_hours_taken(self):
        filters = {
            'date': ['>=',self.get_payroll_date_beginning_for_this_month() ] ,
            'docstatus' : 1 ,
            'employee_name' : self.employee_name ,
            'type' : "Exit" ,
            "time_difference" : ["is", "set"] 
        }
        
        all_times_for_employee = frappe.db.get_list("Permissions" , filters, pluck="time_difference")
        return sum(all_times_for_employee, datetime.timedelta()) 
    
    
    def get_payroll_date_beginning_for_this_month(self):

        converted_penalty_date = getdate(today())

        return getdate(self.get_settings().get("payroll_date_beginning")).replace(month=converted_penalty_date.month , year=converted_penalty_date.year)