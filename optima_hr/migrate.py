import frappe 
from frappe import _


def after_migrate():
    add_meta_data_in_leave_type()


def add_meta_data_in_leave_type():
    
    frappe.db.sql(""" 
        UPDATE 
            `tabDocField` SET options = "Daily\nMonthly\nQuarterly\nHalf-Yearly\nYearly"
        WHERE parent = 'Leave Type' AND fieldname = 'earned_leave_frequency' 
    """ ,auto_commit=True)