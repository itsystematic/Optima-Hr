
import frappe
from erpnext.accounts.party import get_party_account
from frappe.utils import getdate , date_diff
from dateutil.relativedelta import relativedelta

@frappe.whitelist()
def get_fields_for_leave_dues(parent,parentfield) :

    label_fields = frappe.db.get_all("Leave Dues Fields"  ,{"parent" : parent, "parentfield" : parentfield }, pluck="field_name")
    fields = list(map(lambda x : x.get("fieldname") , filter(lambda x : x.get("label") in label_fields ,frappe.get_meta("Salary Structure Assignment").fields) ))

    return fields

@frappe.whitelist()
def get_total_amount_for_salary_structure_assignment(employee , include_fields) :

    if not include_fields : return 0.00

    last_doc = frappe.db.get_all("Salary Structure Assignment" , {
        "employee" : employee ,
        "docstatus" : 1,
    },include_fields , order_by="creation desc" , limit=1 , as_list=True)

    total = sum(map(lambda x : x , last_doc[0])) if last_doc else 0.00
    return total

@frappe.whitelist()
def get_last_work_days_salary(employee, company, end_work_date):
    payroll_date_beginning = get_optima_hr_payroll_date_beginning(company)
    
    end_work_date = getdate(end_work_date)
    payroll_start_date = get_payroll_start_date(payroll_date_beginning, end_work_date)
    days_to_pay = date_diff(end_work_date, payroll_start_date) + 1
    
    fields = get_fields_for_leave_dues(company, "component_to_calculate_cost_of_day")
    total = get_total_amount_for_salary_structure_assignment(employee, fields)
    salary_per_day = total / 30
    remaining_salary = salary_per_day * days_to_pay
    
    return remaining_salary

def get_optima_hr_payroll_date_beginning(company):
    payroll_date_beginning = frappe.db.get_value("Optima HR Setting", {"company": company}, "payroll_date_beginning")
    return getdate(payroll_date_beginning)


def get_payroll_start_date(payroll_date_beginning, end_work_date):
    payroll_day = payroll_date_beginning.day
    
    if end_work_date.day >= payroll_day:
        return end_work_date.replace(day=payroll_day)
    else:
        previous_month = end_work_date - relativedelta(months=1)
        return previous_month.replace(day=payroll_day)

@frappe.whitelist()
def create_payment_entry(doc) :
    import json

    doc = json.loads(doc)
    
    party_account = get_party_account("Employee" , doc.get("employee") , doc.get("company"))
    grand_total = 0
    outstanding_amount = 0
    allocated_amount = 0
    
    if doc.get("doctype") == "Leave Dues" :
        grand_total = doc.get("total_dues_amount")
        outstanding_amount = doc.get("total_dues_amount") - doc.get("paid_amount")
        allocated_amount = doc.get("total_dues_amount") - doc.get("paid_amount")
        
    elif  doc.get("doctype") == "End of Service Benefits":
        grand_total = doc.get("final_result")
        outstanding_amount = doc.get("final_result") - doc.get("paid_amount")
        allocated_amount = doc.get("final_result") - doc.get("paid_amount")
        
    
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.posting_date = getdate()
    payment_entry.company = doc.get("company")
    payment_entry.payment_type = "Pay"
    payment_entry.party_type = "Employee"
    payment_entry.party = doc.get("employee") 
    payment_entry.paid_to = party_account
    
    if doc.get("doctype") == "Leave Dues" :
        payment_entry.paid_amount = doc.get("total_dues_amount")
        payment_entry.received_amount = doc.get("total_dues_amount")
    elif  doc.get("doctype") == "End of Service Benefits":
        payment_entry.paid_amount = doc.get("final_result")
        payment_entry.received_amount = doc.get("final_result")
        
    # payment_entry.source_exchange_rate = 1
    # payment_entry.target_exchange_rate = 1

    payment_entry.append(
        "references",
        {
            "reference_doctype": doc.get("doctype"),
            "reference_name": doc.get("name"),
            "bill_no": doc.get("posting_date"),
            "due_date": doc.get("posting_date"),
            "total_amount": grand_total,
            "outstanding_amount":  outstanding_amount,
            "allocated_amount": allocated_amount,
        },
    )
    payment_entry.setup_party_account_field()
    payment_entry.set_missing_values()
    payment_entry.set_missing_ref_details()
    payment_entry.set_amounts()
    
    return payment_entry