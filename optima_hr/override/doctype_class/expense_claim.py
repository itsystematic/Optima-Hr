"""Custom Expense Claim behavior for Optima HR.

This override keeps the existing Optima HR purchase-invoice payment flow, where
an Expense Claim can settle linked Purchase Invoices by updating their
`paid_amount` and `outstanding_amount`.

The implementation intentionally uses the current Purchase Invoice outstanding as
the base for manual-testing simplicity. This mirrors the temporary behavior the
team requested while keeping the logic isolated inside Optima HR.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from frappe import _
from frappe.utils import flt
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim


class CustomExpenseClaim(ExpenseClaim):
    """Extend Expense Claim to support linked Purchase Invoice settlement."""

    taxable_amount: float

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.taxable_amount = 0

    def validate(self) -> None:
        """Keep standard validation and enforce full advance allocation."""
        super().validate()
        self.validate_total_amount_invoice_equal_total_advances()

    def validate_total_amount_invoice_equal_total_advances(self) -> None:
        """Require linked advances to match the claimed invoice total."""
        if not self.advances:
            return

        total_amount_of_invoices = sum(flt(expense.get("amount")) for expense in self.expenses)
        total_allocated_amount_of_advances = sum(
            flt(advance.get("allocated_amount", 0)) for advance in self.advances
        )

        if total_amount_of_invoices != total_allocated_amount_of_advances:
            frappe.throw(
                _("The Amount Must be same {0} , {1}").format(
                    total_amount_of_invoices, total_allocated_amount_of_advances
                )
            )

    def on_cancel(self) -> None:
        """Reverse linked Purchase Invoice totals when the claim is cancelled."""
        super().on_cancel()
        self.sync_purchase_invoices(reverse=True)

    def on_submit(self) -> None:
        """Apply linked Purchase Invoice totals when the claim is submitted."""
        super().on_submit()
        self.sync_purchase_invoices()

    def sync_purchase_invoices(self, reverse: bool = False) -> None:
        """Sync each linked Purchase Invoice using the summed claim amount."""
        for purchase_invoice, amount in get_linked_purchase_invoices_with_amount(self.expenses).items():
            sync_purchase_invoice_totals(purchase_invoice, amount, reverse=reverse)

    def get_gl_entries(self) -> list[dict[str, Any]]:
        """Build GL entries while preserving supplier linkage for PI-backed rows."""
        gl_entry: list[dict[str, Any]] = []
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

        for expense in self.expenses:
            purchase = None
            if expense.get("purchase_invoice"):
                purchase = frappe.get_doc("Purchase Invoice", expense.purchase_invoice)

            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": expense.default_account,
                        "debit": expense.sanctioned_amount,
                        "debit_in_account_currency": expense.sanctioned_amount,
                        # Preserve supplier context so these rows stay tied to the PI flow.
                        "party_type": "Supplier" if purchase else "",
                        "party": purchase.get("supplier") if purchase else "",
                        "against": self.employee,
                        "cost_center": expense.get("cost_center") or self.get("cost_center"),
                    },
                    item=expense,
                )
            )

        for advance in self.advances:
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": advance.advance_account,
                        "credit": advance.allocated_amount,
                        "credit_in_account_currency": advance.allocated_amount,
                        "against": ",".join([d.default_account for d in self.expenses]),
                        "party_type": "Employee",
                        "party": self.employee,
                        "against_voucher_type": "Employee Advance",
                        "against_voucher": advance.employee_advance,
                        "cost_center": self.get("cost_center"),
                    }
                )
            )

        self.add_tax_gl_entries(gl_entry)

        if self.is_paid and self.grand_total:
            payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
            payment_cost_center = self.get("cost_center")
            gl_entry.append(
                self.get_gl_dict(
                    {
                        "account": payment_account,
                        "credit": self.grand_total,
                        "credit_in_account_currency": self.grand_total,
                        "against": self.employee,
                        "cost_center": payment_cost_center,
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

    def calculate_total_amount(self) -> None:
        """Recalculate totals and taxable amount from the expense rows."""
        self.total_claimed_amount = 0
        self.total_sanctioned_amount = 0
        self.taxable_amount = 0

        for expense in self.get("expenses"):
            if self.approval_status == "Rejected":
                expense.sanctioned_amount = 0.0
            if expense.get("with_vat", 0) == 1:
                self.taxable_amount += flt(expense.sanctioned_amount)

            self.total_claimed_amount += flt(expense.amount)
            self.total_sanctioned_amount += flt(expense.sanctioned_amount)

    @frappe.whitelist()
    def calculate_taxes(self) -> None:
        """Recompute tax rows after taxable expense totals change."""
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
def validate_outstanding_amount(purchase_invoice: str = "", amount: float = 0.0) -> Any:
    """Ensure the linked Purchase Invoice can absorb the requested amount."""
    ref_doc = frappe.get_doc("Purchase Invoice", purchase_invoice)

    if ref_doc.outstanding_amount < amount:
        frappe.throw(_("The Amount Must be Smaller Than purchase invoice Amount {}").format(purchase_invoice))

    if ref_doc.get("is_return") == 1:
        frappe.throw(_("Can 't Pay Returned Invoice {}").format(purchase_invoice))

    return ref_doc


def get_linked_purchase_invoices_with_amount(expenses: Iterable[Any]) -> dict[str, float]:
    """Group expense rows by Purchase Invoice so each invoice is updated once."""
    purchase_invoices: dict[str, float] = {}
    for expense in expenses:
        if expense.purchase_invoice and flt(expense.amount):
            purchase_invoices.setdefault(expense.purchase_invoice, 0.0)
            purchase_invoices[expense.purchase_invoice] += flt(expense.amount)

    return purchase_invoices


def sync_purchase_invoice_totals(
    purchase_invoice: str, amount: float, reverse: bool = False
) -> None:
    """Adjust the linked Purchase Invoice using its current stored totals.

    This intentionally uses the invoice's current outstanding amount instead of
    a ledger recalculation because the team requested the simpler behavior for
    manual testing.
    """
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

    # Reload before status update so ERPNext evaluates the latest stored totals.
    ref_doc.reload()
    ref_doc.set_status(update=True)
