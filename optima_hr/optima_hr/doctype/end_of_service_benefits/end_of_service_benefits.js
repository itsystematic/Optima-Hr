// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('End of Service Benefits', {
    setup: function(frm) {
        frm.custom_make_buttons = {};
    },

    refresh: function(frm) {
        frm.trigger("add_buttons");
        if(frm.doc.employee != null){ 
            frm.trigger("get_optima_hr_settings");
        }
    },
    end_work_date: function(frm) {
        frm.trigger("get_last_work_days_salary");
    },
    employee: function(frm) {
        frm.trigger("is_salary_structured_employee");
        frm.trigger("calc_salary_allawance");
        frm.trigger("calc_total_salary");
        frm.trigger("get_optima_hr_settings");
    },

    validate: function(frm) {
      if (!frm.doc.is_travel_cost){
        frm.set_value("ticket_type", 0);
        frm.set_value("ticket_cost", 0);
        frm.set_df_property("ticket_cost", "hidden", 1);
      }  
    },
    add_buttons: function(frm) {
        if (
            frm.doc.docstatus === 1 &&
            0 < frm.doc.paid_amount <= frm.doc.final_result 
        ) {
            frm.add_custom_button(__("Create Payment Entry"), () => {
                frappe.call({
                    method: "optima_hr.optima_hr.utils.create_payment_entry",
                    args: {
                        doc: frm.doc,
                    },
                    callback: (r) => {
                        if (r.message) {
                            var doclist = frappe.model.sync(r.message);
                            frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                        }
                    },
                });
            });
        }
    },

    is_salary_structured_employee: function(frm) {
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_salary_structure_assignment_for_employee",
            args: {
                employee: frm.doc.employee
            },
            callback: (r) => {
                if(r.message){
                    frm.set_value("base_salary", r.message.base);
                } else {
                    frappe.throw("No salary structure found for this employee");
                }
            }
        });
    },

    get_optima_hr_settings: function(frm) {
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_optima_hr_settings",
            args: {
                name: frm.doc.company
            },
            callback: (r) => {
                if(r.message){
                    if(r.message.allow_to_edit_start_work_date == 1){
                        frm.set_df_property('start_work_date', 'read_only', 0);  
                    } else {
                        frm.set_df_property('start_work_date', 'read_only', 1);
                    }
                    if(r.message.allow_to_edit_total_salary == 1){
                        frm.set_df_property('total_salary', 'read_only', 0);
                    } else {
                        frm.set_df_property('total_salary', 'read_only', 1);
                    }
                    if(r.message.allow_to_edit_last_work_days_salary == 1){
                        frm.set_df_property('last_work_days_salary', 'read_only', 0);
                    } else {
                        frm.set_df_property('last_work_days_salary', 'read_only', 1);
                    }
                }
            }
        });
    },

    calc_salary_allawance: function(frm) {
        fields = frappe.call({
            method: "optima_hr.optima_hr.utils.get_fields_for_leave_dues",
            args:{
                parent: frm.doc.company,
                parentfield: "required_allowance"
            },
            callback: (r) => {
                if(r.message){
                    frappe.call({
                        method:"optima_hr.optima_hr.utils.get_total_amount_for_salary_structure_assignment",
                        args:{
                            employee: frm.doc.employee,
                            include_fields: r.message
                        },
                        callback: (res) => {
                            console.log(res);
                            frm.set_value("salary_allowance", res.message);
                            frm.set_value("total_salary", res.message + frm.doc.base_salary);
                        }
                    })
                }
            }
        })
    },
    get_last_work_days_salary: function(frm) {
        frappe.call({
            method: "optima_hr.optima_hr.utils.get_last_work_days_salary",
            args:{
                employee: frm.doc.employee,
                company: frm.doc.company,
                end_work_date: frm.doc.end_work_date
            },
            callback: (r) => {
                if(r.message){
                    console.log(r.message);
                    frm.set_value("last_work_days_salary", r.message);
                }
            }
        })
    },
});