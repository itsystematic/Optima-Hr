from datetime import timedelta
from erpnext import get_default_company
import frappe
from frappe.utils import getdate
from hrms.hr.doctype.attendance.attendance import mark_bulk_attendance , get_unmarked_days


def make_attendance_absent_for_unmarked_employee() :

    employess = get_employees_has_unmarked_days()

    for employee in employess :
        unmarked_days = get_unmarked_days(
            employee.get("employee") ,
            getdate(str(getdate() - timedelta(days=90)) ),
            getdate(),
            1
        )     
        if not unmarked_days :
            continue
        mark_bulk_attendance({
            "employee" : employee.get("employee") ,
            "unmarked_days" : unmarked_days ,
            "status" : "Absent",
            "company" : get_default_company()
        })

def get_employees_has_unmarked_days() :
    
    return frappe.db.sql("""
        SELECT
            se.employee
        FROM `tabSet Employee Absent` se
        LEFT JOIN `tabEmployee` e
            ON e.name = se.employee
        WHERE e.status = 'Active'
        
    """,as_dict=1)
    