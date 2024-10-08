// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr.end_of_service");

optima_hr.end_of_service.EndOfService = class EndOfService extends frappe.ui.form.Controller {
    employee(){
        this.is_salary_structured_employee();
    }
    is_salary_structured_employee(employee){
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service.end_of_service.get_salary_structure_assignment_for_employee",
            args: {
                employee: this.frm.doc.employee
            },
            callback: (r) => {
                if(r.message){
                    this.frm.set_value("base_salary", r.message.base)
                }else{
                    frappe.throw("No salary structure found for this employee")
                }
            }
        })
    }
    
}

extend_cscript(cur_frm.cscript, new optima_hr.end_of_service.EndOfService({ frm: cur_frm }));
