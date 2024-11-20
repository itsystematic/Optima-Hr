// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salary Effects", {
    onload: function(frm){
        frm.set_query('procedure', 'employees_component', () => {
            return {
                filters: {
                    salary_effect : 1
                }
            }
        })
        frm.set_query('employee_id', 'employees_component', () => {
            return {
                filters: {
                    company : frm.doc.company
                }
            }
        })
        
    },
    
// -----------------  Dialog Popup for Employee Selection   -----------------
    // refresh: function(frm) {
    //     frm.add_custom_button('Select Employees',()=>{
    //         employee_selection(frm)
    //     }).css({'background-color':'black','color':'#fff','font-size':'12px','font-weight':'bold'})
    // },
	// employee(frm){ 
        // employee_selection(frm)
        // if(frm.doc.employee){
        //     var row  =  frm.add_child("employees_component", {
        //         "employee_id": frm.doc.employee,
        //     });
        // }
        // frm.refresh_field("employees_component")
    // },
    // employees_component_add: function(frm, cdt, cdn){
    //     // get_hourly_rate(frm, cdt, cdn)
    //     if(frm.doc.employee){
    //         var row  =  frm.add_child("employees_component", {
    //             "employee_id": frm.doc.employee,
    //         });
    //         frm.refresh_field("employees_component")
    //     }
    // }
});
frappe.ui.form.on("Employees Salary Effect", {
    qty:function(frm, cdt, cdn){

        let row = locals[cdt][cdn];
        if(row.qty){
            get_hourly_rate(frm, cdt, cdn)
        }        
    },
    procedure(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        

        if(row.procedure){
            get_hourly_rate(frm, cdt, cdn)
        }
    },
    employee_id: function(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if(row.employee_id && row.procedure && row.qty){
            get_hourly_rate(frm, cdt, cdn)
        }
    },
    employees_component_add: function(frm, cdt, cdn){
        if(frm.doc.employee){
            let current_row = locals[cdt][cdn];
            current_row.employee_id = frm.doc.employee
        }
        frm.refresh_field("employees_component")
    }
});



function get_hourly_rate(frm, cdt, cdn){
    let row = frappe.get_doc(cdt,cdn)
    if(row.employee_id){
        frappe.call({
            doc : frm.doc,
            method : 'get_percent_hour' ,
            args : {
                employee : row.employee_id,
                component : row.procedure,
                qty : row.qty
            },
            callback : (r) => {
                if (row.procedure) {
                    row.amount = r.message
                    frm.refresh_field("employees_component")
                }
                
            }
        })
        
    }
        
}







// -----------------  Dialog Popup for Employee Selection   -----------------
// function employee_selection(frm, cdt, cdn){
    
//     new frappe.ui.form.MultiSelectDialog({
//         doctype: "Employee",
//         target: this.cur_frm,
//         setters: {
//             // custom_project: null,
//             // status: null
//         },
//         add_filters_group: true,
//         date_field: "transaction_date",
//         columns: ["name"],
//         primary_action_label: "Add Employees",
//         action(selections) {
//             console.log(selections);
//             for(var i = 0;i < selections.length;i++){
//                 var row  =  cur_frm.add_child("employees_component");
//                 row.employee_id = selections[i]
//             }
//             cur_frm.refresh_field("employees_component")
//             this.dialog.hide();
//         },
        
//     });
    
// }
