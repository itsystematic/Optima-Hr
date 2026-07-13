
frappe.ui.form.on("Expense Claim Type", {
	refresh: function (frm) {
		frm.fields_dict["accounts"].grid.get_field("default_account").get_query = function (
			doc,
			cdt,
			cdn,
		) {

			var d = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					root_type: ["in" , frm.doc.deferred_expense_account ? ["Asset" ]: ["liability" , "Expense"]],
					company: d.company,
				},
			};
		};
	},
});