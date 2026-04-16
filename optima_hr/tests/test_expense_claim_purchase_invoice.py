from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from optima_hr.override.doctype_class.expense_claim import (
    get_linked_purchase_invoices_with_amount,
    sync_purchase_invoice_totals,
    validate_outstanding_amount,
)


class TestExpenseClaimPurchaseInvoice(FrappeTestCase):
    def test_linked_purchase_invoices_are_grouped_by_amount(self):
        expense_rows = [
            Mock(purchase_invoice="PINV-TEST-0001", amount=100),
            Mock(purchase_invoice="PINV-TEST-0001", amount=90),
            Mock(purchase_invoice="PINV-TEST-0002", amount=20),
            Mock(purchase_invoice=None, amount=50),
        ]

        amounts = get_linked_purchase_invoices_with_amount(expense_rows)

        self.assertEqual(amounts, {"PINV-TEST-0001": 190.0, "PINV-TEST-0002": 20.0})

    @patch("optima_hr.override.doctype_class.expense_claim.validate_outstanding_amount")
    @patch("optima_hr.override.doctype_class.expense_claim.frappe.db.set_value")
    def test_sync_purchase_invoice_totals_updates_invoice(self, set_value, validate_outstanding_amount):
        purchase_invoice = Mock()
        purchase_invoice.paid_amount = 0
        purchase_invoice.outstanding_amount = 190
        purchase_invoice.reload = Mock()
        purchase_invoice.set_status = Mock()
        validate_outstanding_amount.return_value = purchase_invoice

        sync_purchase_invoice_totals("PINV-TEST-0001", 190)

        set_value.assert_called_once_with(
            "Purchase Invoice",
            "PINV-TEST-0001",
            {"paid_amount": 190, "outstanding_amount": 0},
            update_modified=False,
        )
        purchase_invoice.reload.assert_called_once_with()
        purchase_invoice.set_status.assert_called_once_with(update=True)

    @patch("optima_hr.override.doctype_class.expense_claim.frappe.get_doc")
    def test_validate_outstanding_amount_uses_current_invoice_outstanding(self, get_doc):
        purchase_invoice = Mock()
        purchase_invoice.get.return_value = 0
        purchase_invoice.outstanding_amount = 190
        get_doc.return_value = purchase_invoice

        ref_doc = validate_outstanding_amount("PINV-TEST-0001", 190)

        self.assertIs(ref_doc, purchase_invoice)
