// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.provide("optima_hr_setting");

optima_hr_setting.OptimaHRSetting = class OptimaHRSetting extends frappe.ui.form.Controller {
    onload() {
        console.log("onload");
        this.fetch_salary_components();
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
        const salary_allowance_table = this.frm.doc.salary_allowance || [];
        this.frm.clear_table('salary_allowance');
        salary_components.forEach(component => {
            const new_row = this.frm.add_child('salary_allowance');
            new_row.salary_component = component.name;
        });
        this.frm.refresh_field('salary_allowance');
    }
}

extend_cscript(cur_frm.cscript, new optima_hr_setting.OptimaHRSetting({ frm: cur_frm }));
