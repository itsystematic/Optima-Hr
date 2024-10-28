// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr_setting");

optima_hr_setting.OptimaHRSetting = class OptimaHRSetting extends frappe.ui.form.Controller {


    refresh() {
        this.setup_queries();
    }

    onload() {
        // this.button = null;
        $(document).ready(() => {
            
            this.handle_buttons();

        })
    }

    handle_buttons() {
        // Button oNe 
        const making_absent = $('button[data-fieldname="making_absent"]');
        making_absent.removeClass('btn-default');
        making_absent.addClass('btn btn-danger text-white fw-bold');
        making_absent.hover(() => {
            making_absent.css('background-color', '#ff000080');
        }, () => {
            making_absent.css('background-color', '');
        })

        this.making_absent_button = making_absent;

        // Button Two
        const make_attendance = $('button[data-fieldname="make_attendance"]');
        make_attendance.removeClass('btn-default');
        make_attendance.addClass('btn btn-success fw-bold');
    }

    setup_queries() {

        let child_table_fields = [
            "required_allowance" , "component_to_calculate_cost_of_day", 
            "component_to_calculate_cost_of_day_for_leaves" ,"leave_dues_fields",
            "employee_salary"
        ];  

        for (let child_table_name of child_table_fields) {
            this.frm.set_query("salary_component",child_table_name, (doc, cdt ,cdn) => {
                let salary_component = doc[child_table_name].map(field => field.salary_component)
                return {
                    filters: [
                        ["Salary Component Account", "company", "=", this.frm.doc.company],
                        ["disabled", "=", 0],
                        ["is_salary_structure_assignment_componant", "=" , 1],
                        ["ssa_name" , "not in" , [null , ""]],
                        ["name" , "not in" , salary_component]
                    ]
                }
            })
        }

        this.frm.set_query("salary_component_for_earning", () => {
            return {
                filters: [
                    ["disabled", "=", 0],
                    ["type", "=", "Earning"],
                    ["Salary Component Account", "company", "=", this.frm.doc.company]
                ]
            }
        })

        this.frm.set_query("salary_component_for_deduction", () => {
            return {
                filters: [
                    ["disabled", "=", 0],
                    ["type", "=", "Deduction"],
                    ["Salary Component Account", "company", "=", this.frm.doc.company]
                ]
            }
        })

        this.frm.set_query("employee", "skip_employee_in_attendance", () => {
            let employee = this.frm.doc.skip_employee_in_attendance.map(employee => employee.employee);
            return {
                filters: {
                    status: "Active",
                    company: this.frm.doc.company,
                    name: ["not in", employee]
                }
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
        const originalText = this.making_absent_button.text();
        this.making_absent_button.html('<span class="spinner-border bg-danger text-white spinner-border-sm" role="status" aria-hidden="true"></span> Loading...');
        frappe.call({
            method: 'optima_hr.optima_hr.doctype.optima_hr_setting.optima_hr_setting.make_attendance_absent_for_unmarked_employee',
            args: {
                from_date: doc.from_date ? doc.from_date : null,
                to_date: doc.to_date ? doc.to_date : null,
            },
            callback: (res) => {
                if (res.message) {
                    this.making_absent_button.html(originalText);
                    frappe.show_alert({ message: __(res.message), indicator: 'green' });
                }
            },
            error: (err) => {
                frappe.show_alert({ message: __(err), indicator: 'red' });
            },
            always: () => {
                this.making_absent_button.html(originalText); // Restore original text

            }
        })
    }

    make_attendance() {
        frappe.call({
            method: 'optima_hr.optima_hr.doctype.optima_hr_setting.optima_hr_setting.make_attendance',
            args : {
                doc : this.frm.doc 
            },
            callback: (res) => {
                frappe.msgprint(__("Attendance Created"));
            }
            // async: true,
        })

    }
}

extend_cscript(cur_frm.cscript, new optima_hr_setting.OptimaHRSetting({ frm: cur_frm }));
