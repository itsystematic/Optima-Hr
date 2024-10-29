// Copyright (c) 2023, IT Systematic and contributors
// For license information, please see license.txt


frappe.ui.form.on('Employee Penalty', {
    refresh(frm) {
        
        frm.set_query("employee" , () => {
            return {
                filters : {
                    company : frm.doc.company ,
                    is_active : 1
                }
            }
        })
	},

    employee : function(frm){
        get_employee_penallty_repeat_state_and_penalty(frm)
    },
    penalty_type : function(frm){
        get_employee_penallty_repeat_state_and_penalty(frm)
    },
})


let get_employee_penallty_repeat_state_and_penalty = (frm) => {
    if (frm.doc.employee && frm.doc.penalty_type){
        frm.call({
            method : 'get_employee_penallty_repeat_state_and_penalty' ,
            doc : frm.doc ,
            freeze: true ,
            freeze_message : "Employee Data"
        })
    }
}