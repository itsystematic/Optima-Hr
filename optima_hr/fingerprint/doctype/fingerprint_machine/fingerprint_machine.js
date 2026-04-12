// Copyright (c) 2025, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fingerprint Machine", {
	refresh(frm) {
        frm.add_custom_button(__('Create Employee Checkin'), function () {
            frappe.show_alert({ message: __('Processing check-ins...'), indicator: 'blue' });

            frappe.call({
                method: 'optima_hr.fingerprint.api.create_employee_checkin',
                callback: function (r) {
                    frappe.msgprint(__(r.message));
                },
                error: function (r) {
                    frappe.msgprint(__(r.message));
                },
            });
        });
	},
});
