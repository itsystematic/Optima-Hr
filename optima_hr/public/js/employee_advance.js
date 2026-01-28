
frappe.ui.form.off("Employee Advance", "make_return_entry");

function makeReturnEntry(frm) {
    frappe.call({
        method: "hrms.hr.doctype.employee_advance.employee_advance.make_return_entry",
        args: {
            employee: frm.doc.employee,
            company: frm.doc.company,
            employee_advance_name: frm.doc.name,
            return_amount: flt(frm.doc.paid_amount - frm.doc.claimed_amount - frm.doc.return_amount),
            advance_account: frm.doc.advance_account,
            mode_of_payment: frm.doc.mode_of_payment,
            currency: frm.doc.currency,
            exchange_rate: frm.doc.exchange_rate,
        },
        callback: function (r) {
            const doclist = frappe.model.sync(r.message);
            frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
        },
    });
}
frappe.ui.form.on("Employee Advance", {
    refresh(frm) {
        if (
            frm.doc.docstatus === 1 &&
            flt(frm.doc.claimed_amount) < flt(frm.doc.paid_amount) - flt(frm.doc.return_amount) &&
            frm.doc.repay_unclaimed_amount_from_salary == 1 &&
            frappe.model.can_create("Additional Salary")
        ) {
            frm.add_custom_button(
                __("Return in One Payment"),
                function () {
                    frm.trigger("return_in_one_payment");
                },
                __("Create")
            );
        }
    },
    make_return_entry(frm) {
        makeReturnEntry(frm);
    },
    return_in_one_payment(frm) {
        makeReturnEntry(frm);
    }
});



