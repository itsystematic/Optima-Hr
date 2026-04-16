import frappe
from frappe import _
from frappe.utils import flt
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account


class CustomExpenseClaim(ExpenseClaim):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taxable_amount = 0

    def validate(self):
        super().validate()
        self.validate_total_amount_invoice_equal_total_advances()

    def validate_total_amount_invoice_equal_total_advances(self):
        if self.advances:
            total_amount_of_invoices = sum(map(lambda x: x.get("amount"), self.expenses))
            total_allocated_amount_of_advances = sum(
                map(lambda x: x.get("allocated_amount", 0), self.advances)
            )
            if total_amount_of_invoices != total_allocated_amount_of_advances:
                frappe.throw(
                    _("The Amount Must be same {0} , {1}").format(
                        total_amount_of_invoices, total_allocated_amount_of_advances
                    )
                )

    def on_cancel(self):
        super().on_cancel()
        self.sync_purchase_invoices(reverse=True)

    def on_submit(self):
        super().on_submit()
        self.sync_purchase_invoices()

    def sync_purchase_invoices(self, reverse: bool = False):
        for purchase_invoice, amount in get_linked_purchase_invoices_with_amount(self.expenses).items():
            sync_purchase_invoice_totals(purchase_invoice, amount, reverse=reverse)

    def get_gl_entries(self):
        gl_entry = []
        self.validate_account_details()

        if self.grand_total:
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": self.payable_account,
                        "credit": self.grand_total,
                        "credit_in_account_currency": self.grand_total,
                        "against": ",".join([d.default_account for d in self.expenses]),
                        "party_type": "Employee",
                        "party": self.employee,
                        "against_voucher_type": self.doctype,
                        "against_voucher": self.name,
                        "cost_center": self.get("cost_center"),
                    },
                    item=self,
                )
            )

        for data in self.expenses:
            if data.get("purchase_invoice"):
                purchase = frappe.get_doc("Purchase Invoice", data.purchase_invoice)
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": data.default_account,
                        "debit": data.sanctioned_amount,
                        "debit_in_account_currency": data.sanctioned_amount,
                        "party_type": "Supplier" if data.get("purchase_invoice") else "",
                        "party": purchase.get("supplier") if data.get("purchase_invoice") else "",
                        "against": self.employee,
                        "cost_center": data.get("cost_center") or self.get("cost_center"),
                    },
                    item=data,
                )
            )

        for data in self.advances:
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": data.advance_account,
                        "credit": data.allocated_amount,
                        "credit_in_account_currency": data.allocated_amount,
                        "against": ",".join([d.default_account for d in self.expenses]),
                        "party_type": "Employee",
                        "party": self.employee,
                        "against_voucher_type": "Employee Advance",
                        "against_voucher": data.employee_advance,
                        "cost_center": self.get("cost_center"),
                    }
                )
            )

        self.add_tax_gl_entries(gl_entry)

        if self.is_paid and self.grand_total:
            payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": payment_account,
                        "credit": self.grand_total,
                        "credit_in_account_currency": self.grand_total,
                        "against": self.employee,
                        "cost_center": data.get("cost_center") or self.get("cost_center"),
                    },
                    item=self,
                )
            )

            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": self.payable_account,
                        "party_type": "Employee",
                        "party": self.employee,
                        "against": payment_account,
                        "debit": self.grand_total,
                        "debit_in_account_currency": self.grand_total,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                    },
                    item=self,
                )
            )

        return gl_entry

    def calculate_total_amount(self):
        self.total_claimed_amount = 0
        self.total_sanctioned_amount = 0
        self.taxable_amount = 0
        for d in self.get("expenses"):
            if self.approval_status == "Rejected":
                d.sanctioned_amount = 0.0
            if d.get("with_vat", 0) == 1:
                self.taxable_amount += flt(d.sanctioned_amount)

            self.total_claimed_amount += flt(d.amount)
            self.total_sanctioned_amount += flt(d.sanctioned_amount)

    @frappe.whitelist()
    def calculate_taxes(self):
        self.calculate_total_amount()
        self.total_taxes_and_charges = 0
        for tax in self.taxes:
            if tax.rate:
                tax.tax_amount = flt(self.taxable_amount) * flt(tax.rate / 100)

            tax.total = flt(tax.tax_amount) + flt(self.taxable_amount)
            self.total_taxes_and_charges += flt(tax.tax_amount)

        self.grand_total = (
            flt(self.total_sanctioned_amount)
            + flt(self.total_taxes_and_charges)
            - flt(self.total_advance_amount)
        )


@frappe.whitelist()
def validate_outstanding_amount(purchase_invoice: str = "", amount: float = 0.00):
    ref_doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if ref_doc.outstanding_amount < amount:
        frappe.throw(_("The Amount Must be Smaller Than purchase invoice Amount {}").format(purchase_invoice))

    if ref_doc.get("is_return") == 1:
        frappe.throw(_("Can 't Pay Returned Invoice {}").format(purchase_invoice))

    return ref_doc


def get_linked_purchase_invoices_with_amount(expenses) -> dict[str, float]:
    purchase_invoices = {}
    for expense in expenses:
        if expense.purchase_invoice and flt(expense.amount):
            purchase_invoices.setdefault(expense.purchase_invoice, 0.0)
            purchase_invoices[expense.purchase_invoice] += flt(expense.amount)
    return purchase_invoices


def sync_purchase_invoice_totals(purchase_invoice: str, amount: float, reverse: bool = False) -> None:
    ref_doc = validate_outstanding_amount(purchase_invoice, 0) if not reverse else frappe.get_doc(
        "Purchase Invoice", purchase_invoice
    )
    direction = -1 if reverse else 1
    updated_paid_amount = flt(ref_doc.paid_amount) + (direction * flt(amount))
    updated_outstanding_amount = flt(ref_doc.outstanding_amount) - (direction * flt(amount))

    frappe.db.set_value(
        "Purchase Invoice",
        purchase_invoice,
        {
            "paid_amount": updated_paid_amount,
            "outstanding_amount": updated_outstanding_amount,
        },
        update_modified=False,
    )

    ref_doc.reload()
    ref_doc.set_status(update=True)
