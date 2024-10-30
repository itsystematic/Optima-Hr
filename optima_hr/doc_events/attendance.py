


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
        Attendance Calculating By Two Way 
            1 - By One Shift 
            2 - By Shift Type ( Standard Shift )

    """

    if doc.shift and doc.in_time and doc.out_time :
        
        optima_hr_settings  = get_optima_hr_settings(doc.company)
        if optima_hr_settings.get("enable_shift_duration") :   
            calculate_auto_attendance_by_one_shift(doc , optima_hr_settings)
        elif optima_hr_settings.get("enable_standard_shift") :
            calculate_auto_attendance_by_shift_type(doc , optima_hr_settings)
        

def calculate_auto_attendance_by_one_shift(doc :dict={} , optima_hr_settings:dict={}):
    shift_type_exists = list(filter(lambda x : x.get("shift_type") == doc.shift , optima_hr_settings.enable_shift_types))

    if not shift_type_exists : return 

    shift_duration = shift_type_exists[0].get("shift_duration") 
    working_hours = doc.get("working_hours")

    if not working_hours :
        working_hours = time_diff_in_hours(doc.out_time , doc.in_time)

    if working_hours  < shift_duration :
        add_deduction_to_employee(doc , shift_duration , working_hours , optima_hr_settings.default_salary_component_for_deduction)
        
    elif working_hours > shift_duration :
        add_earning_to_employee(doc , shift_duration , working_hours , optima_hr_settings.default_salary_component_for_over_time)



def add_deduction_to_employee(doc , shift_duration , working_hours , salary_component):
    
    price_of_hour = ( get_employee_salary(doc.employee , "employee_salary") / 30 ) / shift_duration
    total_minute =  ( shift_duration - working_hours ) * 60 

    filters = {"parentfield": "late_or_early_checkin" , "parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['>',total_minute ] }
    or_filters = {"parentfield": "late_or_early_checkin" , "parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['=',0 ] }
    penalty_value = frappe.db.get_all("Auto Attendance Settings" ,filters=filters,or_filters= or_filters , fields=["value"])

    if penalty_value :

        penalty = penalty_value[0].get("value") * price_of_hour
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount = penalty ,
            salary_component= salary_component,
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )
        
        
def add_earning_to_employee(doc , shift_duration , working_hours , salary_component):
    
    price_of_hour = ( get_employee_salary(doc.employee , "employee_salary") / 30 ) / shift_duration
    total_minute =  ( working_hours - shift_duration  ) * 60 
    filters = {"parentfield": "overtime" ,"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['>=',total_minute ] }
    or_filters = {"parentfield": "overtime" ,"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['=',0 ] }
    penalty_value = frappe.db.get_all("Auto Attendance Settings"  ,filters=filters,or_filters= or_filters , fields=["value"])

    if penalty_value :
        penalty = penalty_value[0].get("value") * price_of_hour
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount = penalty ,
            salary_component= salary_component,
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )



def calculate_auto_attendance_by_shift_type(doc:dict={} , optima_hr_settings:dict={}):
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
        
        if converted_shift_start_time.time() < converted_in_time.time()  and  optima_hr_settings.get("enable_add_deduction_for_checkin_late") == 1:
            check_if_employee_get_late(converted_in_time , converted_shift_start_time , doc ,optima_hr_settings )
            #    5:00  <   4:30
        if converted_shift_end_time.time()  >  converted_out_time.time() and  optima_hr_settings.get("enable_add_deduction_for_checkout_early") == 1:
            chek_if_employee_exit_early(converted_out_time ,converted_shift_end_time , doc , optima_hr_settings)

        if converted_shift_end_time.time()  < converted_out_time.time() and  optima_hr_settings.get("enable_add_overtime_to_employee") == 1:
            check_if_employee_has_over_time(converted_out_time ,converted_shift_end_time , converted_shift_start_time , doc , optima_hr_settings)


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
    
    filters = {"parentfield": "late_checkin" , "parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['>',total_minute ] }
    or_filters = {"parentfield": "late_checkin" , "parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['=',0 ] }
    penalty_allowed = frappe.db.get_list("Auto Attendance Settings" ,filters=filters,or_filters= or_filters , fields=["from" , "to" , "value"])
    if penalty_allowed :
        deduction_amount =  (get_employee_salary(doc.get("employee") , "employee_salary") / 30 ) * penalty_allowed[0].get("value" , 0)
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
    filters = {"parentfield": "early_checkout" ,"parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['>',total_minute ] }
    or_filters = {"parentfield": "early_checkout" ,"parent" : doc.get("shift") ,'from': ['<',total_minute ] ,'to': ['=',0 ] }
    penalty_allowed = frappe.db.get_list("Auto Attendance Settings" ,filters=filters,or_filters= or_filters , fields=["from" , "to" , "value"])
    if penalty_allowed :
        deduction_amount =  (get_employee_salary(doc.get("employee") , "employee_salary") / 30 ) * penalty_allowed[0].get("value" , 0)
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
    
    filters = {"parentfield": "overtime" ,"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['>=',total_minute ] }
    or_filters = {"parentfield": "overtime" ,"parent" : doc.get("shift") ,'from': ['<=',total_minute ] ,'to': ['=',0 ] }
    over_time_details = frappe.db.get_list("Auto Attendance Settings"  ,filters=filters,or_filters= or_filters , fields=["from" , "to" , "value"])
    
    if over_time_details :
        earning_amount =  (( get_employee_salary(doc.employee) / 30 ) / shift_hours ) * over_time_details[0].get("value" , 0)
        create_additional_salary(
            employee=doc.employee,
            posting_date=doc.attendance_date,
            amount=earning_amount,
            salary_component=hr_settings.get("default_salary_component_for_over_time"),
            ref_doctype=doc.doctype,
            ref_docname=doc.name
        )



