# Copyright (c) 2024, IT Systematic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class VacationStartWork(Document):
    
    def on_submit(self):
        self.change_status_to_out()
        self.change_final_status_leaves_dues("Out")
        self.make_employee_vecationer_as_left("Active" , submit = False)
    
    def on_cancel(self):
        self.change_final_status_leaves_dues("In")
        self.make_employee_vecationer_as_left("Inactive" )
        
    def change_status_to_out(self):
        
        leave_dues = self.get_last_doc_if_exists()
        
        if not leave_dues :
            frappe.throw(_("There is no leave due for this employee"))
        
        if not self.applicable_leave_dues :
            self.db_set("applicable_leave_dues" , leave_dues.name)
            
                
    def change_final_status_leaves_dues(self , status) :
        frappe.db.set_value("Leave Dues", self.applicable_leave_dues, "final_status", status)
        
            
    @frappe.whitelist()
    def get_last_doc_if_exists(self) :        
        leaves_dues = frappe.db.get_all('Leave Dues', filters={
            "employee": self.employee,
            "docstatus": 1 ,
            "final_status" : "In"
        },fields = [
            "name" ,
            "leave_start_date",
            "leave_end_date"
            
        ], order_by = "creation desc" , limit = 1)
        
        
        return leaves_dues[0] if leaves_dues else []
    
        
    def make_employee_vecationer_as_left(self , status , submit=True) :
        
        frappe.db.set_value("Employee" , self.employee ,{
            "status" : status ,
            "is_vacationer" : submit
        }, update_modified=False)
        