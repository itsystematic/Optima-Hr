// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr.end_of_service_benefits");

optima_hr.end_of_service_benefits.EndOfServiceBenefits = class EndOfServiceBenefits extends frappe.ui.form.Controller {


    // field method
    employee(){
        this.is_salary_structured_employee();
        this.get_optima_hr_settings();
    }

    // helper method
    is_salary_structured_employee(){
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_salary_structure_assignment_for_employee",
            args: {
                employee: this.frm.doc.employee
            },
            callback: (r) => {
                if(r.message){
                    let salary_allowance = this.frm.doc.salary_allowance || 0;
                    let total_s = salary_allowance + r.message.base
                    this.frm.set_value("base_salary", r.message.base)
                    this.frm.set_value("total_salary",total_s )
                }else{
                    frappe.throw("No salary structure found for this employee")
                }
            }
        })
    }

    get_optima_hr_settings(){
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_optima_hr_settings",
            args: {
                name: this.frm.doc.employee_company
            },
            callback: (r) => {
                if(r.message){
                    this.apply_optima_hr_settings(r.message)
                }
            }
        })
    }

    apply_optima_hr_settings(settings){
        if(settings.allow_to_edit_start_work_date == 1){
           this.frm.set_df_property('start_work', 'read_only', 0);  
        }else{
            this.frm.set_df_property('start_work', 'read_only', 1);
        }
        if(settings.allow_to_edit_total_salary){
            this.frm.set_df_property('total_salary', 'read_only', 0);
        }else{
            this.frm.set_df_property('total_salary', 'read_only', 1);
        }
    }
}

extend_cscript(cur_frm.cscript, new optima_hr.end_of_service_benefits.EndOfServiceBenefits({ frm: cur_frm }));
