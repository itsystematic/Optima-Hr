from hrms.payroll.doctype.additional_salary.additional_salary import AdditionalSalary
import frappe
from frappe import _

class CustomAdditionalSalary(AdditionalSalary):
    
    '''
    26/02/2026
    
    This class for :
            - Allow multi additional salary (employee advance) in the same month by the same component
            - Disable Update  TO make sure return amount get from gl not just from additional salary doctype to avoid any mismatch
            - Validate Amount wise advance amount
    '''
    
    def validate(self):
        super().validate()
        self.validate_amount_wise_advance_amount()

    def validate_recurring_additional_salary_overlap(self):
        """ pass it for now to allow multi additional salary (employee advance) in the same month by the same component """
        pass

    def update_return_amount_in_employee_advance(self) :
        """ Disable Update  TO make sure return amount get from gl not just from additional salary doctype to avoid any mismatch """
        pass



    def validate_amount_wise_advance_amount(self):
        """ Validate Amount wise advance amount """
        if self.ref_doctype and self.ref_doctype == "Employee Advance":
            if self.amount <= 0:
                frappe.throw(
                    _("Amount must be greater than zero for Amount Wise Advance component.")
                )
            # Check if an Employee Advance with the same amount already exists
            employee_advance_amount = frappe.get_value("Employee Advance",
                                                        self.ref_docname,
                                                        "advance_amount")
            if employee_advance_amount < self.amount:
                frappe.throw(
                    _("It seems that the amount not valid for this advance, Please check the advance amount in Employee Advance {0}").format(self.ref_docname)
                )
