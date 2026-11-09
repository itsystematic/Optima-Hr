import frappe 
from frappe import _

from optima_hr import features


def after_migrate():
    add_meta_data_in_leave_type()
    features.apply()


def add_meta_data_in_leave_type():
    
    frappe.db.sql(""" 
        UPDATE 
            `tabDocField` SET options = "Daily\nMonthly\nQuarterly\nHalf-Yearly\nYearly"
        WHERE parent = 'Leave Type' AND fieldname = 'earned_leave_frequency' 
    """ ,auto_commit=True)