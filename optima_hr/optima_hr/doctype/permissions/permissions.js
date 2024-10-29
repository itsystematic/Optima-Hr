// Copyright (c) 2023, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on('Permissions', {

	employee_name: function(frm) {

		frm.trigger("get_total_time_remaining") ;
	},

	get_total_time_remaining(frm){
		frappe.call({
			method: 'get_total_time_remaining',
			doc : frm.doc,
			callback: (r) => {
				frm.set_value("remaining_hours" , r.message);
				frm.refresh_field('remaining_hours');
			},
		})
	},

	from_time(frm){
		frm.trigger("set_time_difference") ;
	},
	to_time(frm){
		frm.trigger("set_time_difference") ;
	},

	set_time_difference(frm){
		frappe.call({
			method: 'set_time_difference',
			doc : frm.doc,
			callback: (r) => {
				frm.refresh_field('time_difference');
			},
		})
	}

});
