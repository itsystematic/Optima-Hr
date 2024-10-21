// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr_setting");

optima_hr_setting.OptimaHRSetting = class OptimaHRSetting extends frappe.ui.form.Controller {


    refresh() {
        this.setup_queries();
        this.get_fields_of_salary_structure_assignment();

    }

    setup_queries() {

        this.frm.set_query("salary_component_for_earning" , () => {
            return {
                filters : [
                    ["disabled" , "=", 0] ,
                    ["type" , "=", "Earning"] ,
                    ["Salary Component Account", "company", "=", this.frm.doc.company]
                ]
            }
        })

        this.frm.set_query("salary_component_for_deduction" , () => {
            return {
                filters : [
                    ["disabled" , "=", 0] ,
                    ["type" , "=", "Deduction"] ,
                    ["Salary Component Account", "company", "=", this.frm.doc.company]
                ]
            }
        })

        this.frm.set_query("employee" , "skip_employee_in_attendance", () => {
            let employee = this.frm.doc.skip_employee_in_attendance.map(employee => employee.employee);
            return {
                filters : {
                    status : "Active",
                    company : this.frm.doc.company,
                    name : ["not in" , employee]
                }
            }
        })
    }

    get_fields_of_salary_structure_assignment() {
        let me = this;
        frappe.call({
            method : "get_fields_of_salary_structure_assignment" ,
            doc : me.frm.doc ,
            callback:(r) =>  {
                me.frm.fields_dict["leave_dues_fields"].grid.get_docfield("field_name").options = r.message
            }
        })
    }

    fetch_salary_components() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Salary Component',
                fields: ['name'],
                limit: 0 
            },
            callback: (response) => {
                if (response.message) {
                    this.populate_salary_allowance_table(response.message);
                }
            }
        });
    }

    making_absent(doc) {
        const button = $('button[data-fieldname="making_absent"]');
        const originalText = button.text();
        button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...');
        frappe.call({
            method: 'optima_hr.optima_hr.doctype.optima_hr_setting.optima_hr_setting.make_attendance_absent_for_unmarked_employee',
            args: {
                from_date: doc.from_date ? doc.from_date : null,
                to_date: doc.to_date ? doc.to_date : null,
            },
            callback: (res) => {
                if (res.message) {
                    button.html(originalText);
                    frappe.show_alert({ message: __(res.message), indicator: 'green' });
                }
            },
            error: (err) => {
                frappe.show_alert({ message: __(err), indicator: 'red' });
            },
            always: () => {
                button.html(originalText); // Restore original text

            }
        })
    }
}

extend_cscript(cur_frm.cscript, new optima_hr_setting.OptimaHRSetting({ frm: cur_frm }));
