

frappe.ui.form.on("Leave Application", {

    refresh(frm) {
        frm.trigger("button_create_leave_dues");
    },

    async button_create_leave_dues(frm) {

        let allow_encashment_response =  await frappe.db.get_value("Leave Type", frm.doc.leave_type, "allow_encashment") ; 
        let submited_leaves_dues = await frappe.db.get_list("Leave Dues" , { 
                filters : {
                    "leave_application" : frm.doc.name ,
                    "docstatus" : 1 ,
                    "employee" : frm.doc.employee
                },
                fields: ["name"], 
            }
        );
        
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.status === "Approved" && 
            allow_encashment_response.message.allow_encashment === 1  &&
            submited_leaves_dues.length === 0
        
        ) {
            frm.add_custom_button(__("Leave Dues"), () => {
                frappe.route_options = {
                    employee: frm.doc.employee || "",
                    leave_application : frm.doc.name || "", 
                    company : frm.doc.company || ""
                };
                frappe.new_doc("Leave Dues");
            } , __("Create"))
        }
    }
})


