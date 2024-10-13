# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate , flt
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account
from optima_hr.optima_hr.utils import(
    get_fields_for_leave_dues,
    get_total_amount_for_salary_structure_assignment
)
from frappe.query_builder.functions import Sum

class LeaveDues(Document):
    
    def validate(self) :
        self.validate_leave_application()


    def validate_leave_application(self) :
        if frappe.db.exists(self.doctype , {
            "leave_application" : self.leave_application ,
            "docstatus" : 1
        }) :
            frappe.throw(_("This Leave Application Already Submitted"))



    def before_save(self) :	
        self.set_total_dues_amount()


    def set_total_dues_amount(self) :
        self.total_dues_amount = (self.leave_dues_amount or 0 ) + (self.travel_ticket_amount or 0) + ( self.other_dues_amount or 0 )


    def on_submit(self) :

        self.make_attendance_vacation("Absent")
        self.make_employee_vecationer_as_left("Inactive")


    def on_cancel(self) :
        
        self.make_attendance_vacation("On Leave" , submit=False)
        self.make_employee_vecationer_as_left("Active" , submit=False)

    def make_attendance_vacation(self , status , submit=True) :

        attendance = frappe.qb.DocType("Attendance")
        query = (
            frappe.qb.update(attendance)
            .set(attendance.is_vacation , submit )
            .set(attendance.status , status)
            .where(attendance.leave_application == self.leave_application)
        
        ).run()
        
        
    def make_employee_vecationer_as_left(self , status , submit=True) :
        
        frappe.db.set_value("Employee" , self.employee ,{
            "status" : status ,
            "is_vacationer" : submit
        }, update_modified=False)


    @frappe.whitelist()
    def calculate_day_cost_for_leave_dues(self) :

        fields = get_fields_for_leave_dues(self.company , "leave_dues_fields")
        total_amount = get_total_amount_for_salary_structure_assignment(self.employee,fields)
        leave_dues_amount = total_amount * (self.leave_duration or 0) / 30

        return leave_dues_amount
    

    def set_status(self, update=False):
        
        if self.paid_amount >= self.total_dues_amount :
            status = "Paid"
    
    def set_total_advance_paid(self) :
        gle = frappe.qb.DocType("GL Entry")

        paid_amount = (
            frappe.qb.from_(gle)
            .select(Sum(gle.debit).as_("paid_amount"))
            .where(
                (gle.against_voucher_type == self.doctype)
                & (gle.against_voucher == self.name)
                & (gle.party_type == "Employee")
                & (gle.party == self.employee)
                & (gle.docstatus == 1)
                & (gle.is_cancelled == 0)
            )
        ).run(as_dict=True)[0].paid_amount or 0

        if paid_amount > flt(self.total_dues_amount):
            frappe.throw(
                _("Row {0}# Paid Amount cannot be greater than Total Dues amount"),
            )
        self.db_set("paid_amount", paid_amount)
        # self.set_status(update=True)





@frappe.whitelist()
def create_payment_entry(doc) :
    import json

    doc = json.loads(doc)
    
    party_account = get_party_account("Employee" , doc.get("employee") , doc.get("company"))
    
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.posting_date = getdate()
    payment_entry.company = doc.get("company")
    payment_entry.payment_type = "Pay"
    payment_entry.party_type = "Employee"
    payment_entry.party = doc.get("employee") 
    payment_entry.paid_to = party_account
    payment_entry.paid_amount = doc.get("total_dues_amount")
    payment_entry.received_amount = doc.get("total_dues_amount")
    # payment_entry.source_exchange_rate = 1
    # payment_entry.target_exchange_rate = 1

    payment_entry.append(
        "references",
        {
            "reference_doctype": doc.get("doctype"),
            "reference_name": doc.get("name"),
            "bill_no": doc.get("posting_date"),
            "due_date": doc.get("posting_date"),
            "total_amount": doc.get("total_dues_amount"),
            "outstanding_amount":  doc.get("total_dues_amount") - doc.get("paid_amount"),
            "allocated_amount": doc.get("total_dues_amount") - doc.get('paid_amount'),
        },
    )
    payment_entry.setup_party_account_field()
    payment_entry.set_missing_values()
    payment_entry.set_missing_ref_details()
    payment_entry.set_amounts()
    
    return payment_entry