// Copyright (c) 2026, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Checklist", {
	refresh(frm) {

	},

	get_employee(frm) {
		if (!frm.doc.date) {
			frappe.msgprint(__("Please select a date first"));
			return;
		}

		frappe.call({
			method: "optima_hr.optima_hr.doctype.daily_checklist.daily_checklist.get_filtered_employees",
			args: {
				date: frm.doc.date,
				department: frm.doc.department,
				designation: frm.doc.designation,
				employee_project: frm.doc.employee_project,
				branch: frm.doc.branch
			},
			callback: function(r) {
				if (r.message) {
					r.message.forEach(function(employee) {
						let row = frm.add_child("table_chlk", {
							employee: employee.name,
							present: 1,
							employee_project: employee.custom_employee_project
						});
					});
					
					frm.refresh_field("table_chlk");
					frappe.msgprint(__("Employees loaded successfully"));
				}
			}
		});
	}
});

frappe.ui.form.on("Daily Checklist Details", {
	present(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.present == 0) {
			row.overtime = "";
			row.deduction = "";
			frm.refresh_field("table_chlk");
		}
	}
});
