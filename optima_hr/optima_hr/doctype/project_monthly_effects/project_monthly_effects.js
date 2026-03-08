// Copyright (c) 2026, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project Monthly Effects", {
	refresh(frm) {
		// Clear existing dashboard comments to prevent duplicates
		frm.dashboard.clear_comment();
		
		if (frm.doc.docstatus == 0) {
			frm.dashboard.add_comment(__("You can Review it during the month and confirm at month closing."), "blue", true);
		}
	},
});
