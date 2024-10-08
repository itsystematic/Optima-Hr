
frappe.ui.form.on('Gratuity Calculator', {
	calculate: function(frm) {
		frm.call({
			method : 'calculation' ,
			doc: frm.doc ,
			freeze: true,
		});

	},
	refresh: function(frm) {
		if(frm.doc.docstatus == 1){
			frm.add_custom_button('Pay',()=>{
				frappe.model.open_mapped_doc({
					method: "hr_ksa.hr_ksa.doctype.gratuity_calculator.gratuity_calculator.make_payment_entry",
					frm: frm
				})
			}
		)}
	},
	employee : function(frm) {
		frm.call({
			method : 'hr_ksa.hr_ksa.doctype.gratuity_calculator.gratuity_calculator.get_employee_details' ,
			args : {
				employee : frm.doc.employee
			},
			callback: (r) => {
				// console.log(r)
				frm.set_value("last_salary_slab_amount" , r.message.last_salary_slab_amount)
				frm.set_value("return_loans" , r.message.return_loans)
				frm.set_value("start_work_date" , r.message.start_work_date)
				frm.set_value("total_salary" , (r.message.last_salary_slab_amount + r.message.salary_allowance))
			} ,
		})
	},
});