// Copyright (c) 2024, IT Systematic Company and contributors
// For license information, please see license.txt

frappe.ui.form.on("HR Letter", {
	hr_letter_template(frm) {
		if (frm.doc.hr_letter_template) {
			frappe.call({
				method: 'optima_hr.optima_hr.doctype.hr_letter_template.hr_letter_template.get_template',
				args: {
					temp: frm.doc.hr_letter_template,
					doc: frm.doc
				},
				callback: function(r) {
                    console.log(r)
					if (r && r.message) {
						frm.set_value("terms", r.message.terms);
					}
				}
			});
		}
	},
});
