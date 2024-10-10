
import frappe
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