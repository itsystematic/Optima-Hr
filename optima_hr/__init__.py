__version__ = "15.0.0"

import frappe

def get_optima_hr_settings(company) :

    return frappe.get_doc("Optima HR Setting", company)


def get_company_setting_with_employee(employee) :
	
    default_company = frappe.db.get_value("Employee" , employee , "company" , cache=True)
    optima_settings = get_optima_hr_settings(default_company)
	
    return optima_settings
	