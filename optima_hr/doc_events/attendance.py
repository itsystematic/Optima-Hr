


import frappe
from frappe import _
from datetime import datetime 
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





def attendance_on_submit(doc:dict={} , event:str=""):
    """_summary_

    Args:
        doc (dict, optional): _description_. Defaults to {}.
        event (str, optional): _description_. Defaults to "".
        
    Base Method :
        Method to Add Additional Salary Deduction or Earning  
            1 =>  Calculate if Employee Check in Early .
            
            2 =>  Calculate if Employee Check Out Late .
            
            3 =>  Calculate if Employee Has Over Time .
            
    """
    if doc.shift and doc.in_time and doc.out_time :
        shift_start_time  , shift_end_time  = frappe.db.get_value("Shift Type", doc.get("shift") , ["start_time" , "end_time"])
        
        if isinstance(doc.in_time , str ) :
            converted_in_time = datetime.strptime(doc.in_time, "%Y-%m-%d %H:%M:%S")
            converted_out_time =  datetime.strptime(doc.out_time, "%Y-%m-%d %H:%M:%S")
            
        elif isinstance(doc.in_time , datetime) :
            converted_in_time  , converted_out_time = doc.in_time , doc.out_time
        # Concat time with Date To Calculate Difference    
        converted_shift_start_time =  datetime.combine(converted_in_time.date()  , datetime.strptime(str(shift_start_time), "%H:%M:%S").time())
        converted_shift_end_time =  datetime.combine(converted_out_time.date() , datetime.strptime(str(shift_end_time), "%H:%M:%S").time())
        hrksa_permission_settings = get_hr_permission_setting()
        
        if converted_shift_start_time.time() < converted_in_time.time()  and  hrksa_permission_settings.get("enable_add_deduction_for_checkin_late") == 1:
            check_if_employee_get_late(converted_in_time , converted_shift_start_time , doc ,hrksa_permission_settings )
            #    5:00  <   4:30
        if converted_shift_end_time.time()  >  converted_out_time.time() and  hrksa_permission_settings.get("enable_add_deduction_for_checkout_early") == 1:
            chek_if_employee_exit_early(converted_out_time ,converted_shift_end_time , doc , hrksa_permission_settings)

        if converted_shift_end_time.time()  < converted_out_time.time() and  hrksa_permission_settings.get("enable_add_overtime_to_employee") == 1:
            check_if_employee_has_over_time(converted_out_time ,converted_shift_end_time , converted_shift_start_time , doc , hrksa_permission_settings)


def check_if_employee_get_late(converted_in_time:datetime ,  converted_shift_start_time:datetime , doc :dict={} , hr_settings = None):
    """_summary_

    Args:
        converted_in_time (datetime): _description_
        converted_shift_start_time (datetime): _description_
        doc (dict, optional): _description_. Defaults to {}.
    Action :
        Create Additional Salary to Employee if Get Late 
    """
    duration = converted_in_time - converted_shift_start_time
    total_minute , total_second = divmod(duration.total_seconds(), 60)
    
    filters = {"parent" : doc.get("shift") ,'from_time': ['<',total_minute ] ,'to_time': ['>',total_minute ] }
    or_filters = {"parent" : doc.get("shift") ,'from_time': ['<',total_minute ] ,'to_time': ['=',0 ] }
    penalty_allowed = frappe.db.get_list("Late Checkin" ,filters=filters,or_filters= or_filters , fields=["from_time" , "to_time" , "penalty"])
    if penalty_allowed :
        deduction_amount =  (get_employee_base_amount(doc.get("employee")) / 30 ) * penalty_allowed[0].get("penalty" , 0)
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount=deduction_amount,
            salary_component= hr_settings.get("default_salary_component_for_check_in_late"),
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )
        

def chek_if_employee_exit_early(
    converted_out_time:datetime ,
    converted_shift_end_time:datetime ,
    doc :dict={},
    hr_settings = None
):
    """_summary_

    Args:
        converted_out_time (datetime): _description_
        converted_shift_end_time (datetime): _description_
        doc (dict, optional): _description_. Defaults to {}.
    Action : 
        Create Additional Salary to Employee if Exit Early 
    """
    duration = converted_shift_end_time - converted_out_time
    
    # Convert to minute 
    total_minute , total_second = divmod(duration.total_seconds(), 60)
    filters = {"parent" : doc.get("shift") ,'from_time': ['<',total_minute ] ,'to_time': ['>',total_minute ] }
    or_filters = {"parent" : doc.get("shift") ,'from_time': ['<',total_minute ] ,'to_time': ['=',0 ] }
    penalty_allowed = frappe.db.get_list("Early Checkout" ,filters=filters,or_filters= or_filters , fields=["from_time" , "to_time" , "penalty"])
    if penalty_allowed :
        deduction_amount =  (get_employee_base_amount(doc.get("employee")) / 30 ) * penalty_allowed[0].get("penalty" , 0)
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount=deduction_amount,
            salary_component=hr_settings.get("default_salary_component_for_check_out_early"),
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )



def check_if_employee_has_over_time(
    converted_out_time:datetime ,
    converted_shift_end_time:datetime ,
    converted_shift_start_time:datetime,  
    doc :dict={},
    hr_settings = None
) :
    """_summary_

    Args:
        converted_out_time (datetime): _description_
        converted_shift_end_time (datetime): _description_
        converted_shift_start_time (datetime): _description_
        doc (dict, optional): _description_. Defaults to {}.
    Action :
        Function to Calculate Difference Time Between Shift End Time and Employee Check out Time To Get Over Time
    """
    duration = converted_out_time - converted_shift_end_time
    shift_hours = time_diff_in_hours(converted_shift_end_time , converted_shift_start_time )
    total_minute , total_second = divmod(duration.total_seconds(), 60)
    
    filters = {"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['>=',total_minute ] }
    or_filters = {"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['=',0 ] }
    over_time_details = frappe.db.get_list("Overtime Details" ,filters=filters,or_filters= or_filters , fields=["from" , "to" , "overtime_value"])
    
    if over_time_details :
        earning_amount =  (( get_employee_base_amount(doc.employee) / 30 ) / shift_hours ) * over_time_details[0].overtime_value
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount=earning_amount,
            salary_component=hr_settings.get("default_salary_component_for_over_time"),
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )



