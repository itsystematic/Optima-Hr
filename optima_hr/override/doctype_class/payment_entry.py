import frappe
from erpnext import get_company_currency
from erpnext.accounts.doctype.payment_entry.payment_entry import (
    PaymentEntry,
    get_bank_cash_account,
    get_reference_details,
)
from erpnext.setup.utils import get_exchange_rate
from hrms.overrides.employee_payment_entry import get_reference_details_for_employee
from frappe.utils import flt

class OptimaPaymentEntry(PaymentEntry) :

    def get_valid_reference_doctypes(self):
        if self.party_type == "Customer":
            return ("Sales Order", "Sales Invoice", "Journal Entry", "Dunning", "Payment Entry")
        elif self.party_type == "Supplier":
            return ("Purchase Order", "Purchase Invoice", "Journal Entry", "Payment Entry")
        elif self.party_type == "Shareholder":
            return ("Journal Entry",)
        elif self.party_type == "Employee":
            return ("Expense Claim", "Journal Entry", "Employee Advance", "Gratuity" , "Leave Dues","End of Service Benefits" )
        # any doctype in optima hr
        
        
    def set_missing_ref_details(
        self,
        force: bool = False,
        update_ref_details_only_for: list | None = None,
        reference_exchange_details: dict | None = None,
    ) -> None:
        for d in self.get("references"):
            if d.allocated_amount:
                if update_ref_details_only_for and (
                    (d.reference_doctype, d.reference_name) not in update_ref_details_only_for
                ):
                    continue

                ref_details = get_payment_reference_details(
                    d.reference_doctype,
                    d.reference_name,
                    self.party_account_currency,
                    self.party_type,
                    self.party,
                )

                # Only update exchange rate when the reference is Journal Entry
                if (
                    reference_exchange_details
                    and d.reference_doctype == reference_exchange_details.reference_doctype
                    and d.reference_name == reference_exchange_details.reference_name
                ):
                    ref_details.update({"exchange_rate": reference_exchange_details.exchange_rate})

                for field, value in ref_details.items():
                    if d.exchange_gain_loss:
                        # for cases where gain/loss is booked into invoice
                        # exchange_gain_loss is calculated from invoice & populated
                        # and row.exchange_rate is already set to payment entry's exchange rate
                        # refer -> `update_reference_in_payment_entry()` in utils.py
                        continue

                    if field == "exchange_rate" or not d.get(field) or force:
                        if self.get("_action") in ("submit", "cancel"):
                            d.db_set(field, value)
                        else:
                            d.set(field, value)

@frappe.whitelist()
def get_payment_reference_details(
    reference_doctype, reference_name, party_account_currency, party_type=None, party=None
):
    if reference_doctype in ("Expense Claim", "Employee Advance", "Gratuity"):
        return get_reference_details_for_employee(reference_doctype, reference_name, party_account_currency)
    elif reference_doctype in ("Leave Dues","End of Service Benefits") :
        # for optima hr doctypes
        return get_reference_details_for_optima(reference_doctype, reference_name, party_account_currency)
    else:
        return get_reference_details(
            reference_doctype, reference_name, party_account_currency, party_type, party
        )

def get_reference_details_for_optima(reference_doctype, reference_name, party_account_currency) :
    total_amount = outstanding_amount = exchange_rate = None
    ref_doc = frappe.get_doc(reference_doctype, reference_name)
    company_currency = ref_doc.get("company_currency") or get_company_currency(ref_doc.company)
    total_amount, exchange_rate = get_total_amount_and_exchange_rate(
        ref_doc, party_account_currency, company_currency
    )

    if reference_doctype == "Leave Dues":
        outstanding_amount = flt(ref_doc.total_dues_amount) - flt(ref_doc.paid_amount)

    elif reference_doctype == "End of Service Benefits" :
        outstanding_amount = flt(ref_doc.final_result) - flt(ref_doc.paid_amount)


    return frappe._dict(
        {
            "due_date": ref_doc.get("posting_date"),
            "total_amount": flt(total_amount),
            "outstanding_amount": flt(outstanding_amount),
            "exchange_rate": flt(exchange_rate),
        }
    )

def get_total_amount_and_exchange_rate(ref_doc, party_account_currency, company_currency):
    total_amount = exchange_rate = None

    if ref_doc.doctype == "Leave Dues" :
        total_amount = ref_doc.total_dues_amount 
    
    if ref_doc.doctype == "End of Service Benefits" :
        total_amount = ref_doc.final_result 


    if not exchange_rate:
        # Get the exchange rate from the original ref doc
        # or get it based on the posting date of the ref doc.
        exchange_rate = ref_doc.get("conversion_rate") or get_exchange_rate(
            party_account_currency, company_currency, ref_doc.posting_date
        )

    return total_amount, exchange_rate