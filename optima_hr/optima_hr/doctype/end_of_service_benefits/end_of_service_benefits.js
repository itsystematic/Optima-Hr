
// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr.end_of_service_benefits");
optima_hr.end_of_service_benefits.EndOfServiceBenefits = class EndOfServiceBenefits extends frappe.ui.form.Controller {
    setup() {
        this.frm.custom_make_buttons = {};
    }

    refresh() {
        this.add_buttons();
        if (this.frm.doc.employee != null) {
            this.get_optima_hr_settings();
        }
    }

    end_work_date() {
        this.get_last_work_days_salary();
        this.get_leave_balance_for_employee();
        this.get_closing_balance();
    }

    employee() {
        this.is_salary_structured_employee();
        this.calc_salary_allawance();
        // this.get_optima_hr_settings();
    }

    is_travel_cost() {
        if (this.frm.doc.is_travel_cost == 0) {
            this.frm.set_value("ticket_type", null);
            this.frm.set_value("ticket_cost", 0);
        }
    }

    add_buttons() {
        if (
            this.frm.doc.docstatus === 1 &&
            0 < this.frm.doc.paid_amount && this.frm.doc.paid_amount <= this.frm.doc.final_result
        ) {
            this.frm.add_custom_button(__("Create Payment Entry"), () => {
                frappe.call({
                    method: "optima_hr.optima_hr.utils.create_payment_entry",
                    args: {
                        doc: this.frm.doc,
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
    }

    is_salary_structured_employee() {
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_salary_structure_assignment_for_employee",
            args: {
                employee: this.frm.doc.employee
            },
            callback: (r) => {
                if (r.message) {
                    this.frm.set_value("base_salary", r.message.base);
                } else {
                    frappe.throw("No salary structure found for this employee");
                }
            }
        });
    }

    get_optima_hr_settings() {
        frappe.call({
            method: "optima_hr.optima_hr.doctype.end_of_service_benefits.end_of_service_benefits.get_optima_hr_settings",
            args: {
                name: this.frm.doc.company
            },
            callback: (r) => {
                console.log(r.message);
                if (r.message) {
                    // Start Work Date
                    this.frm.set_df_property('start_work_date', 'read_only', r.message.allow_to_edit_start_work_date !== 1);
    
                    // Total Salary
                    this.frm.set_df_property('total_salary', 'read_only', r.message.allow_to_edit_total_salary !== 1);
    
                    // Last Work Days Salary
                    this.frm.set_df_property('last_work_days_salary', 'read_only', r.message.allow_to_edit_last_work_days_salary !== 1);
    
                    // Employee Advance Amount
                    this.frm.set_df_property('closing_cr', 'read_only', r.message.allow_to_edit_employee_advance_amount !== 1);
                    this.frm.set_df_property('closing_de', 'read_only', r.message.allow_to_edit_employee_advance_amount !== 1);
    
                    // Outstanding Leave Amount
                    this.frm.set_df_property('outstanding_leave_balance_amount', 'read_only', r.message.allow_to_edit_outstanding_leave_amount !== 1);
                }
            }
        });
    }

    calc_salary_allawance() {
        frappe.call({
            method: "optima_hr.optima_hr.utils.get_fields_for_leave_dues",
            args: {
                parent: this.frm.doc.company,
                parentfield: "required_allowance"
            },
            callback: (r) => {
                if (r.message) {
                    frappe.call({
                        method: "optima_hr.optima_hr.utils.get_total_amount_for_salary_structure_assignment",
                        args: {
                            employee: this.frm.doc.employee,
                            include_fields: r.message
                        },
                        callback: (res) => {
                            this.frm.set_value("salary_allowance", res.message);
                            this.frm.set_value("total_salary", res.message + this.frm.doc.base_salary);
                        }
                    })
                }
            }
        })
    }

    get_last_work_days_salary() {
        frappe.call({
            method: "optima_hr.optima_hr.utils.get_last_work_days_salary",
            args: {
                employee: this.frm.doc.employee,
                company: this.frm.doc.company,
                end_work_date: this.frm.doc.end_work_date
            },
            callback: (r) => {
                if (r.message) {
                    this.frm.set_value("last_work_days_salary", r.message.remaining_salary);
                    this.frm.set_value("last_work_days", r.message.days_to_pay);
                }
            }
        })
    }

    get_leave_balance_for_employee() {
        frappe.call({
            method: "optima_hr.optima_hr.utils.get_leave_balance_amount",
            args: {
                company: this.frm.doc.company,
                employee: this.frm.doc.employee,
                leave_date: this.frm.doc.end_work_date
            },
            callback: (r) => {
                if (r.message) {
                    this.frm.set_value("outstanding_leave_balance", r.message.outstanding_leave_balance);
                    this.frm.set_value("outstanding_leave_balance_amount", r.message.outstanding_leave_amount);
                }
            }
        })
    }

    get_closing_balance() {
        frappe.call({
            method: "optima_hr.optima_hr.utils.get_closing_balances",
            args:{
                company: this.frm.doc.company,
                to_date:this.frm.doc.end_work_date,
                party:this.frm.doc.employee
            },
            callback:(r)=>{
                if(r.message){
                    this.frm.set_value("closing_cr",r.message.closing_credit);
                    this.frm.set_value("closing_de",r.message.closing_debit);
                }
            }
        })
    }
}

extend_cscript(cur_frm.cscript, new optima_hr.end_of_service_benefits.EndOfServiceBenefits({ frm: cur_frm }));