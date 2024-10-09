// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Dues", {
        refresh(frm) {
                frm.trigger("add_buttons");
        },

        add_buttons(frm) {
                if (
                        frm.doc.docstatus === 0 &&
                        !frm.is_new() &&
                        frm.doc.payment_entry_created == 0
                ) {
                        frm.page.clear_primary_action();
                        frm.add_custom_button(__("Create Payment Entry"), () => {
                                frappe.call({
                                        method:
                                                "optima_hr.optima_hr.doctype.leave_dues.leave_dues.create_payment_entry",
                                        args: {
                                                company: frm.doc.company,
                                                employee: frm.doc.employee,
                                                paid_amount: frm.doc.total_dues_amount,
                                        },
                                        callback: (r) => {
                                                if (r.message) {
                                                        frm.set_value({
                                                                payment_entry: r.message,
                                                                payment_entry_created: 1,
                                                        });
                                                        frm.save();
                                                        cur_frm.reload_doc();
                                                        frappe.set_route("Form", "Payment Entry", r.message);
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
                        method:
                                "optima_hr.optima_hr.doctype.leave_dues.leave_dues.calculate_day_cost_for_leave_dues",
                        args: {
                                doc: frm.doc,
                        },
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
