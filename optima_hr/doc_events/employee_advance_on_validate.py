import frappe
from frappe import _
from frappe.utils import flt

def employee_advance_on_validate(doc, method):
    # Custom validation logic
    if doc.advance_amount <= 0:
        frappe.throw(_("Advance amount must be greater than zero."))
    
    # Validate advance amount against allowed percentage
    validate_advance_amount_against_allowed_percentage(doc)

def validate_advance_amount_against_allowed_percentage(doc): 
    """Validate that advance amount does not exceed allowed percentage of basic salary"""
    
    # Get employee advance allowed percentage
    employee_advance_allowed = frappe.db.get_value("Employee", doc.employee, "employee_advance_allowed")
    
    # If no percentage is set, no validation needed (no limit)
    if not employee_advance_allowed:
        return
    
    # Get the latest salary structure assignment for the employee
    salary_structure_assignment = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": doc.employee,
            "docstatus": 1
        },
        ["name", "base"],
        order_by="from_date desc",
        as_dict=True
    )
    
    if not salary_structure_assignment:
        frappe.throw(_("No active Salary Structure Assignment found for employee {0}").format(doc.employee))
    
    basic_salary = salary_structure_assignment.get("base", 0)
    
    if not basic_salary:
        frappe.throw(_("Basic salary not found in Salary Structure Assignment for employee {0}").format(doc.employee))
    
    # Calculate maximum allowed advance amount
    max_allowed_advance = flt(basic_salary) * flt(employee_advance_allowed) / 100
    
    # Validate advance amount
    if flt(doc.advance_amount) > max_allowed_advance:
        frappe.throw(_(
            "You can't make Advance amount ({0}) because it is more than {1}% of basic salary ({2}).\nMaximum allowed advance is {3}.\nIf you want to edit the allowed percentage, please contact your manager."
        ).format(
            frappe.format_value(doc.advance_amount, {"fieldtype": "Currency"}),
            flt(employee_advance_allowed),
            frappe.format_value(basic_salary, {"fieldtype": "Currency"}),
            frappe.format_value(max_allowed_advance, {"fieldtype": "Currency"})
        ).replace('\n', '<br>'))
