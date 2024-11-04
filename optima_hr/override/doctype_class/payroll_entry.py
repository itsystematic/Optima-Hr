
import frappe
import erpnext 
from frappe import _
from frappe.utils import flt
from optima_hr.optima_hr.utils import get_optima_hr_settings
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry , get_accounting_dimensions


class OptimaPayrollEntry(PayrollEntry):

    """ 
        Override PayrollEntry make_accrual_jv_entry 
            - Optima Payroll Entry Work if Enable In Setting 

        This Updates in Payroll Entry alone not in Payroll Entry
        This Additions not in Payroll Entry 
    
    """

    def make_accrual_jv_entry(self , submitted_salary_slips):

        optima_setting = get_optima_hr_settings(self.company)

        if optima_setting.components_accounts_distribution_per_party_in_payable_payroll:
            self.make_optima_accrual_jv_entry( submitted_salary_slips , optima_setting)
        
        else :
            super().make_accrual_jv_entry(submitted_salary_slips)



    def make_optima_accrual_jv_entry(self, submitted_salary_slips , optima_setting):
        self.check_permission("write")
        employee_wise_accounting_enabled = frappe.db.get_single_value(
            "Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
        )
        self.employee_based_payroll_payable_entries = {}
        self._advance_deduction_entries = []

        earnings = (
            self.get_optima_salary_component_total(
                component_type="earnings",
                employee_wise_accounting_enabled=employee_wise_accounting_enabled,
            )
            or {}
        )

        deductions = (
            self.get_optima_salary_component_total(
                component_type="deductions",
                employee_wise_accounting_enabled=employee_wise_accounting_enabled,
            )
            or {}
        )
        # payroll_payable_account = self.payroll_payable_account
        # jv_name = ""
        precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
        
        # print(precision)
        if earnings or deductions:
            accounts = []
            currencies = []
            payable_amount = 0
            accounting_dimensions = get_accounting_dimensions() or []
            company_currency = erpnext.get_company_currency(self.company)
            payable_amount = self.get_optima_payable_amount_for_earnings_and_deductions(
                accounts,
                earnings,
                deductions,
                currencies,
                company_currency,
                accounting_dimensions,
                precision,
                payable_amount,
            )
            
            payable_amount = self.set_accounting_entries_for_advance_deductions(
                accounts,
                currencies,
                company_currency,
                accounting_dimensions,
                precision,
                payable_amount,
            )
            
            self.set_payable_amount_against_payroll_payable_account(
                accounts,
                currencies,
                company_currency,
                accounting_dimensions,
                precision,
                payable_amount,
                self.payroll_payable_account,
                employee_wise_accounting_enabled,
            )

            self.make_journal_entry(
                accounts,
                currencies,
                self.payroll_payable_account,
                voucher_type="Journal Entry",
                user_remark=_("Accrual Journal Entry for salaries from {0} to {1}").format(
                    self.start_date, self.end_date
                ),
                submit_journal_entry=True,
                submitted_salary_slips=submitted_salary_slips,
                enable_submit = False if optima_setting.make_draft_journal_entry_for_payable_payroll else True
            )

    def get_optima_salary_component_total(
        self,
        component_type=None,
        employee_wise_accounting_enabled=False,
    ):
        salary_components = self.get_salary_components(component_type)
        if salary_components:
            component_dict = {}
            self.employee_cost_centers = {}
            
            for item in salary_components:
                
                if not self.should_add_component_to_accrual_jv(component_type, item):
                    continue
                
                employee_cost_centers = self.get_payroll_cost_centers_for_employee(
                    item.employee, item.salary_structure
                )
                
                employee_advance = self.get_advance_deduction(component_type, item)
                
                for cost_center, percentage in employee_cost_centers.items():
                    amount_against_cost_center = flt(item.amount , 2) * percentage / 100
                    
                    if employee_advance:
                        self.add_advance_deduction_entry(
                            item, amount_against_cost_center, cost_center, employee_advance
                        )
                    else:
                        key = (item.salary_component, cost_center , item.employee )
                        component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center
                        
                    if employee_wise_accounting_enabled:
                        self.set_employee_based_payroll_payable_entries(
                            component_type, item.employee, amount_against_cost_center
                        )

            account_details = self.get_optima_account(component_dict=component_dict)

            return account_details

    def get_optima_account(self, component_dict=None):
        account_dict = {}
        for key, amount in component_dict.items():
            account = self.get_salary_component_account(key[0])
            account_dict[(account, key[1] , key[2])] = account_dict.get((account, key[1] , key[2]), 0) + amount
        return account_dict
    
    def get_optima_payable_amount_for_earnings_and_deductions(
        self,
        accounts,
        earnings,
        deductions,
        currencies,
        company_currency,
        accounting_dimensions,
        precision,
        payable_amount,
    ):
        # Earnings
        for acc_cc, amount in earnings.items():
            payable_amount = self.get_optima_accounting_entries_and_payable_amount(
                acc_cc[0],
                acc_cc[1] or self.cost_center,
                amount,
                currencies,
                company_currency,
                payable_amount,
                accounting_dimensions,
                precision,
                party = acc_cc[2],
                entry_type="debit",
                accounts=accounts,
            )

        # Deductions
        for acc_cc, amount in deductions.items():
            payable_amount = self.get_optima_accounting_entries_and_payable_amount(
                acc_cc[0],
                acc_cc[1] or self.cost_center,
                amount,
                currencies,
                company_currency,
                payable_amount,
                accounting_dimensions,
                precision,
                party = acc_cc[2],
                entry_type="credit",
                accounts=accounts,
            )

        return payable_amount
    
    def get_optima_accounting_entries_and_payable_amount(
        self,
        account,
        cost_center,
        amount,
        currencies,
        company_currency,
        payable_amount,
        accounting_dimensions,
        precision,
        entry_type="credit",
        party=None,
        accounts=None,
        reference_type=None,
        reference_name=None,
        is_advance=None,
    ):

        exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
            account, amount, company_currency, currencies
        )

        row = {
            "account": account,
            "exchange_rate": flt(exchange_rate),
            "cost_center": cost_center,
            "project": self.project,
        }

        if entry_type == "debit":
            payable_amount += flt(amount, precision)
            row.update(
                {
                    "debit_in_account_currency": flt(amt, precision),
                }
            )
        elif entry_type == "credit":
            payable_amount -= flt(amount, precision)
            row.update(
                {
                    "credit_in_account_currency": flt(amt, precision),
                }
            )
        else:
            row.update(
                {
                    "credit_in_account_currency": flt(amt, precision),
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                }
            )

        if party:
            
            row.update(
                {
                    "party_type": "Employee",
                    "party": party,
                    "cost_center": frappe.db.get_value("Employee" , party , "payroll_cost_center") or cost_center
                }
            )
            
        if reference_type:
            row.update(
                {
                    "reference_type": reference_type,
                    "reference_name": reference_name,
                    "is_advance": is_advance,
                }
            )

        self.update_accounting_dimensions(
            row,
            accounting_dimensions,
        )

        if amt:
            accounts.append(row)

        return payable_amount
    
    def make_journal_entry(
        self,
        accounts,
        currencies,
        payroll_payable_account=None,
        voucher_type="Journal Entry",
        user_remark="",
        submitted_salary_slips: list | None = None,
        submit_journal_entry=False,
        enable_submit = True
    ) -> str:
        multi_currency = 0
        if len(currencies) > 1:
            multi_currency = 1

        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = voucher_type
        journal_entry.user_remark = user_remark
        journal_entry.company = self.company
        journal_entry.posting_date = self.posting_date

        journal_entry.set("accounts", accounts)
        journal_entry.multi_currency = multi_currency

        if voucher_type == "Journal Entry":
            journal_entry.title = payroll_payable_account

        journal_entry.save(ignore_permissions=True)

        try:
            if submit_journal_entry and enable_submit: 
                journal_entry.submit()

            if submitted_salary_slips:
                self.set_journal_entry_in_salary_slips(submitted_salary_slips, jv_name=journal_entry.name)

        except Exception as e:
            if type(e) in (str, list, tuple):
                frappe.msgprint(e)

            self.log_error("Journal Entry creation against Salary Slip failed")
            raise

        return journal_entry