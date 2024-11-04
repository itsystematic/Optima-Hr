# Copyright (c) 2023, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from optima_hr.optima_hr.utils import (
    create_additional_salary ,
    get_total_amount_for_salary_structure_assignment ,
    get_fields_for_leave_dues,
    get_employee_salary
)
from frappe.utils import  time_diff  ,getdate , today 
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
        self.get_employee_default_shift()
        if self.type != "Exit":
            self.extra_hour = None
            self.remaining_hours = None
    
    def on_submit(self):
        self.create_additional_salary()

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
            'date': ['>=',frappe.utils.getdate(self.date)] ,
            'docstatus' : 1 ,
            'employee_name' : self.employee_name ,
            'type' : "Exit"
            }
            number_of_permission = frappe.db.get_list('Permissions', filters=filters,  fields=["COUNT(name) as name"])
            if number_of_permission[0].get("name") >= self.get_settings().get("default_permissions_per_day") :
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
        
    def on_cancel(self):
        self.cancel_doctype_link()

    @frappe.whitelist()
    def get_total_time_remaining(self):
        self.extra_hour = ""
        self.number_of_hours_for_deduction = None
        if self.time_difference:
            if self.allowed_hour and self.get_settings().get("enable_calculate_permission_by_hours") == 1 or self.get_settings().get("enable_standard_shift") == 1:    
                all_times_for_employee = self.get_total_hours_taken()   
                total_delta = self.allowed_hour - all_times_for_employee   
                
                if self.type == "Exit":
                    if self.time_difference > total_delta:
                        
                        # requested time exceeds remaining allowed time
                        if self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 0:
                            frappe.throw(_("The Maximum Working Hours have been Exhausted {0}".format(
                                self.get_settings().allowed_permission_hours)))
                        
                        # Calculate extra hours that exceed the allowed
                        if all_times_for_employee > self.allowed_hour:
                            self.extra_hour = self.time_difference.total_seconds()
                            self.number_of_hours_for_deduction = round((self.extra_hour / 3600), 2)
                            self.remaining_hours = None
                        else :
                            self.extra_hour = self.time_difference.total_seconds() - total_delta.total_seconds()
                            self.number_of_hours_for_deduction = round((self.extra_hour / 3600), 2)
                            self.remaining_hours = None
                    else:
                        # requested time is within remaining allowed time
                        self.remaining_hours = total_delta - self.time_difference
                        self.extra_hour = ""
                        self.number_of_hours_for_deduction = None
                else:
                    self.remaining_hours = total_delta
                    self.extra_hour = ""
                    
                return total_delta
        
    
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
    
    
    def create_additional_salary(self):
        salary_component = frappe.db.get_value("Optima HR Setting" , self.company , "default_salary_component_for_permissions")
        if self.get_settings().get("enable_add_deduction_after_permissions__hours_allowed") == 1 and self.type == "Exit" and self.extra_hour: 
            amount = self.get_salary_component_for_deductions_total_amount()
            doc = create_additional_salary(
                employee=self.employee_name,
                posting_date=self.date,
                amount=amount ,
                salary_component= salary_component,
                ref_doctype=self.doctype,
                ref_docname=self.name
                )
    def cancel_doctype_link(self):
        
        if additional_salary := frappe.db.exists("Additional Salary" , {"ref_doctype" : self.doctype , "ref_docname" : self.name}) :
            frappe.get_doc("Additional Salary", additional_salary).cancel()
            frappe.delete_doc("Additional Salary", additional_salary)

    def get_salary_component_for_deductions_total_amount(self):
        if self.type == "Exit" and self.extra_hour :
            fields = get_fields_for_leave_dues(self.company, "salary_component_for_deduction")
            total = get_total_amount_for_salary_structure_assignment(self.employee_name, fields)
            shift_duration = self.get_shift_settings()
            salary_per_hour = (total / 30) / shift_duration
            total_deductions = (self.extra_hour / 3600) * salary_per_hour
            return total_deductions
    
    def get_employee_default_shift(self):        
        shift = frappe.db.get_value("Employee" , {"name": self.employee_name} , "default_shift")
        self.shift_type = shift
        return shift
    
    def get_enabled_shifts(self):
            shifts = frappe.db.get_all(
                "Enable Shift Types",
                filters={"parent": self.company, "parentfield": "enable_shift_types" , "shift_type" : self.shift_type},
                fields=["shift_type", "shift_duration"]
            )
            res = {
                "shifts": shifts[0].shift_type if shifts else None,
                "shift_duration": shifts[0].shift_duration if shifts else 8.0
            }
            return res
        
    def get_shift_settings(self):
        settings = self.get_settings()
        if settings.get("enable_standard_shift") ==1 :
            shift_duration  = self.get_employee_shift_duration(standard_shift=1)
        elif settings.get("enable_shift_duration") ==1 :
            shift_duration  = self.get_employee_shift_duration(standard_shift=0)
        else:
            shift_duration = 8.0
        return shift_duration
    
    def get_employee_shift_duration(self, standard_shift):
        if standard_shift == 1 : 
            employee_shift = self.get_employee_default_shift()
            shift = frappe.get_doc("Shift Type", employee_shift)
            shift_duration = time_diff(shift.start_time , shift.end_time)
        else:
            shift_duration = self.get_enabled_shifts().get("shift_duration")
            return shift_duration
        
        if self.shift_type :
            return abs(shift_duration.total_seconds() / 3600)
        else :
            return 8.0
            