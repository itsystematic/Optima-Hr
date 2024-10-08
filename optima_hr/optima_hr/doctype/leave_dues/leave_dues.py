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
            .set(attendance.custom_is_vacation , submit )
            .set(attendance.status , status)
            .where(attendance.leave_application == self.leave_application)
        
        ).run()
        
        
    def make_employee_vecationer_as_left(self , status , submit=True) :
        
        frappe.db.set_value("Employee" , self.employee ,{
            "status" : status ,
            "custom_is_vacationer" : submit
        }, update_modified=False)

@frappe.whitelist()
def calculate_day_cost_for_leave_dues(doc) :


        setting_check = frappe.db.get_single_value("HR Permission Settings","calculate_cost_of_day")
        last_doc = frappe.get_last_doc("Salary Structure Assignment" , {
            "employee" : doc.employee ,
            "docstatus" : 1,
        })

        if last_doc :
            if setting_check == 1 :
                doc.leave_dues_amount = ((last_doc.base or 0) * (doc.leave_duration or 0) / 30)
                
                return doc.leave_dues_amount
            else:
                doc.leave_dues_amount = ((last_doc.base or 0) +
                                    (last_doc.home_allowance or 0) +  
                                    (last_doc.mobile_allowance or 0) + 
                                    (last_doc.travel_allowance or 0)) * (doc.leave_duration or 0) / 30
                return doc.leave_dues_amount
        else :
            frappe.throw(_("There is no Salary Structure assigned to {}").format(doc.employee))

        
        




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