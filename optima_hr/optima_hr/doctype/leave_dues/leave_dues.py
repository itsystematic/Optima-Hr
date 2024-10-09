# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account


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


    def get_fields_for_leave_dues(self) :

        label_fields = frappe.db.get_all("Leave Dues Fields"  ,{"company" : self.company }, pluck="field_name")
        fields = list(map(lambda x : x.get("fieldname") , filter(lambda x : x.get("label") in label_fields ,frappe.get_meta("Salary Structure Assignment").fields) ))

        return fields
    
    def get_total_amount_for_salary_structure_assignment(self , fields) :
        last_doc = frappe.db.get_all("Salary Structure Assignment" , {
            "employee" : self.employee ,
            "docstatus" : 1,
        },fields=fields , order_by="creation desc" , limit=1 , as_list=True)
        return sum(map(lambda x : x[0]))

    @frappe.whitelist()
    def calculate_day_cost_for_leave_dues(self) :

        fields = self.get_fields_for_leave_dues()
        total_amount = self.get_total_amount_for_salary_structure_assignment(fields)
        leave_dues_amount = total_amount * (self.leave_duration or 0) / 30

        return leave_dues_amount





@frappe.whitelist()
def create_payment_entry(company , employee , paid_amount) :
    
    
    party_account = get_party_account("Employee" , employee , company)
    
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.posting_date = getdate()
    payment_entry.company = company
    payment_entry.payment_type = "Pay"
    payment_entry.party_type = "Employee"
    payment_entry.party = employee
    payment_entry.paid_to = party_account
    payment_entry.paid_amount = paid_amount
    payment_entry.received_amount = paid_amount
    payment_entry.source_exchange_rate = 1
    payment_entry.target_exchange_rate = 1
    # payment_entry.validate()
    payment_entry.save()
    
    return payment_entry