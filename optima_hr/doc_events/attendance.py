


import frappe
from frappe import _
from frappe.utils import time_diff_in_hours
from optima_hr.optima_hr.utils import (
    create_additional_salary ,
    get_employee_salary ,
    get_optima_hr_settings
)


def attendance_on_submit(doc:dict={} , event:str=""):
    """_
    
        This Structure For Ensan Company

    """
    if doc.shift and doc.in_time and doc.out_time and doc.status in ["Present" , "Absent"]:

        optima_hr_settings  = get_optima_hr_settings(doc.company)

        if not optima_hr_settings.get("enable_shift_duration") : return  
        
        shift_type_exists = list(filter(lambda x : x.get("shift_type") == doc.shift , optima_hr_settings.enable_shift_types))

        if not shift_type_exists : return 

        shift_duration = shift_type_exists[0].get("shift_duration") 
        working_hours = doc.get("working_hours")
        
        if not working_hours :
            working_hours = time_diff_in_hours(doc.out_time , doc.in_time)

        # base_salary = get_employee_salary(doc.employee)
        
        if working_hours  < shift_duration :
            add_deduction_to_employee(doc , shift_duration , working_hours , optima_hr_settings.salary_component_for_deduction)
            
        elif working_hours > shift_duration :
            add_earning_to_employee(doc , shift_duration , working_hours , optima_hr_settings.salary_component_for_earning)


def add_deduction_to_employee(doc , shift_duration , working_hours , salary_component):
    
    difference_between_time =  shift_duration - working_hours
    price_of_hour = ( get_employee_salary(doc.employee) / 30 ) / shift_duration
    penalty = difference_between_time * price_of_hour

    create_additional_salary(
        employee=doc.employee,
        posting_date=doc.attendance_date,
        amount = penalty ,
        salary_component= salary_component,
        ref_doctype=doc.doctype,
        ref_docname=doc.name
    )
        
        
def add_earning_to_employee(doc , shift_duration , working_hours , salary_component):
    
    difference_between_time = working_hours - shift_duration
    price_of_hour = ( get_employee_salary(doc.employee) / 30 ) / shift_duration
    penalty = difference_between_time * price_of_hour * 1.5
    
    create_additional_salary(
        employee=doc.employee,
        posting_date=doc.attendance_date,
        amount = penalty ,
        salary_component= salary_component,
        ref_doctype=doc.doctype,
        ref_docname=doc.name
    )