


import frappe


def default_shift_assignment(doc:dict={} , event:str="") -> None:

    frappe.db.set_value("Employee", doc.employee, "default_shift", doc.shift_type)

    frappe.db.commit()

