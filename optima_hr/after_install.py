

import frappe 

def delete_genders():
    genders = frappe.get_all("Gender", pluck="name") 
    
    accepted = ['Male', 'Female']
    
    for gender in genders:
        if gender not in accepted:
            print(gender)
            frappe.delete_doc("Gender", gender)