// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr_setting");

optima_hr_setting.OptimaHRSetting = class OptimaHRSetting extends frappe.ui.form.Controller {
    onload() {
        this.fetch_salary_components();
    }

    refresh() {
        this.get_fields_of_salary_structure_assignment();
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

    populate_salary_allowance_table(salary_components) {
        this.frm.clear_table('salary_allowance');
        salary_components.forEach(component => {
            const new_row = this.frm.add_child('salary_allowance');
            new_row.salary_component = component.name;
        });
        this.frm.refresh_field('salary_allowance');
    }
}

extend_cscript(cur_frm.cscript, new optima_hr_setting.OptimaHRSetting({ frm: cur_frm }));
