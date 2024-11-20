// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Dues", {
        setup(frm) {
                // frm.ignore_doctypes_on_cancel_all = ["Payment Entry" , "GL Entry"];
        },
        refresh(frm) {
                // frm.ignore_doctypes_on_cancel_all = ["Payment Entry"];
                frm.trigger("add_buttons");
                if (frm.is_new() && !frm.doc.leave_application) {
                        frm.disable_form();
                        frm.dashboard.set_headline(__("This Doctype is Secondary, It Depends on a Valid Leave, Please Create It from The Leave Application"), "yellow");    
                }

        },

        add_buttons(frm) {
                if (
                        frm.doc.docstatus === 1 &&
                        frm.doc.paid_amount < frm.doc.leave_dues_amount
                ) {
                        // frm.page.clear_primary_action();
                        frm.add_custom_button(__("Create Payment Entry"), () => {
                                frappe.call({
                                        method:
                                                "optima_hr.optima_hr.utils.create_payment_entry",
                                        args: {
                                                doc: frm.doc,
                                        },
                                        callback: (r) => {
                                                if (r.message) {
                                                        var doclist = frappe.model.sync(r.message);
                                                        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                                                }
                                        },
                                });
                        });
                }

                // if (frm.doc.docstatus == 0 && frm.doc.payment_entry_created == 1 ) {

                // }
        },
        leave_dues_amount(frm) {
                calculate_total_dues_amount(frm);
        },
        travel_ticket_amount(frm) {
                calculate_total_dues_amount(frm);
        },
        other_dues_amount(frm) {
                calculate_total_dues_amount(frm);
        },
        leave_application(frm) {
                frappe.call({
                        method: "calculate_day_cost_for_leave_dues",
                        doc : frm.doc,
                        callback: function (r) {
                                if (r.message) {
                                        frm.set_value("leave_dues_amount", r.message);
                                }
                        },
                });
        },
});

let calculate_total_dues_amount = (frm) => {
        frm.set_value(
                "total_dues_amount",
                (frm.doc.leave_dues_amount || 0) +
                (frm.doc.travel_ticket_amount || 0) +
                (frm.doc.other_dues_amount || 0)
        );
};
