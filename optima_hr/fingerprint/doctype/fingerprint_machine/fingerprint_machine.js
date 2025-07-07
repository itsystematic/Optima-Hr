// Copyright (c) 2025, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fingerprint Machine", {
	refresh(frm) {
        frm.add_custom_button(__('Create Employee Checkin'), function () {
            frappe.show_alert({ message: __('Processing check-ins...'), indicator: 'blue' });

            frappe.call({
                method: 'optima_hr.fingerprint.utils.create_employee_checkin',
                callback: function (r) {
                    frappe.msgprint(__('Employee check-ins created successfully.'));
                },
                error: function () {
                    frappe.msgprint(__('Failed to create check-ins.'));
                },
                always: function () {
                    frappe.hide_alert();
                }
            });
        });
	},
});
