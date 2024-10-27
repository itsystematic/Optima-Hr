
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip, set_loan_repayment, get_period_factor
import frappe
from frappe import _
from frappe.utils import flt , cint , getdate,add_days  ,rounded


class CustomSalarySlip(SalarySlip):
    
    def calculate_net_pay(self):
        if not getattr(self, "_salary_structure_doc", None):
            self._salary_structure_doc = frappe.get_cached_doc("Salary Structure", self.salary_structure)
        
        if self.salary_structure and self.is_new() :
            self.calculate_component_amounts("earnings")

        # get remaining numbers of sub-period (period for which one salary is processed)
        if self.payroll_period:
            self.remaining_sub_periods = get_period_factor(
                self.employee, self.start_date, self.end_date, self.payroll_frequency, self.payroll_period
            )[1]
        print(self.gross_pay)

        self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
        self.base_gross_pay = flt(
            flt(self.gross_pay) * flt(self.exchange_rate), self.precision("base_gross_pay")
        )
        print(self.gross_pay)

        if self.salary_structure and self.is_new() :
            self.calculate_component_amounts("deductions")

        if self.get("loans") :
            
            set_loan_repayment(self)
        
        self.set_precision_for_component_amounts()
        self.set_net_pay()
        self.compute_income_tax_breakup()
        self.calculate_custom_cost_to_company_ctc()
    # def get_working_days_details(self, lwp=None, for_preview=0):
    #     payroll_settings = frappe.get_cached_value(
    #         "Payroll Settings",
    #         None,
    #         (
    #             "payroll_based_on",
    #             "include_holidays_in_total_working_days",
    #             "consider_marked_attendance_on_holidays",
    #             "daily_wages_fraction_for_half_day",
    #             "consider_unmarked_attendance_as",
    #         ),
    #         as_dict=1,
    #     )

    #     consider_marked_attendance_on_holidays = (
    #         payroll_settings.include_holidays_in_total_working_days
    #         and payroll_settings.consider_marked_attendance_on_holidays
    #     )

    #     daily_wages_fraction_for_half_day = (
    #         flt(payroll_settings.daily_wages_fraction_for_half_day) or 0.5
    #     )

    #     working_days = 30
    #     # working_days = date_diff(self.end_date, self.start_date) + 1
    #     if for_preview:
    #         self.total_working_days = working_days
    #         self.payment_days = working_days
    #         return

    #     holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
    #     working_days_list = [
    #         add_days(getdate(self.start_date), days=day) for day in range(0, working_days)
    #     ]

    #     if not cint(payroll_settings.include_holidays_in_total_working_days):
    #         working_days_list = [i for i in working_days_list if i not in holidays]

    #         working_days -= len(holidays)
    #         if working_days < 0:
    #             frappe.throw(_("There are more holidays than working days this month."))

    #     if not payroll_settings.payroll_based_on:
    #         frappe.throw(_("Please set Payroll based on in Payroll settings"))

    #     if payroll_settings.payroll_based_on == "Attendance":
    #         actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(
    #             holidays, daily_wages_fraction_for_half_day, consider_marked_attendance_on_holidays
    #         )
    #         self.absent_days = absent
    #     else:
    #         actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(
    #             holidays, working_days_list, daily_wages_fraction_for_half_day
    #         )

    #     if not lwp:
    #         lwp = actual_lwp
    #     elif lwp != actual_lwp:
    #         frappe.msgprint(
    #             _("Leave Without Pay does not match with approved {} records").format(
    #                 payroll_settings.payroll_based_on
    #             )
    #         )

    #     self.leave_without_pay = lwp
    #     self.total_working_days = working_days

    #     payment_days = self.get_payment_days(payroll_settings.include_holidays_in_total_working_days)

    #     if flt(payment_days) > flt(lwp):
    #         self.payment_days = flt(payment_days) - flt(lwp)

    #         if payroll_settings.payroll_based_on == "Attendance":
    #             self.payment_days -= flt(absent)

    #         consider_unmarked_attendance_as = payroll_settings.consider_unmarked_attendance_as or "Present"

    #         if (
    #             payroll_settings.payroll_based_on == "Attendance"
    #             and consider_unmarked_attendance_as == "Absent"
    #         ):
    #             unmarked_days = self.get_unmarked_days(payroll_settings.include_holidays_in_total_working_days)
    #             self.absent_days += unmarked_days  # will be treated as absent
    #             self.payment_days -= unmarked_days
    #     else:
    #         self.payment_days = 0  
    
    # def get_payment_days(self, include_holidays_in_total_working_days):
    #     if self.joining_date and self.joining_date > getdate(self.end_date):
    #         # employee joined after payroll date
    #         return 0

    #     if self.relieving_date:
    #         employee_status = frappe.db.get_value("Employee", self.employee, "status")
    #         if self.relieving_date < getdate(self.start_date) and employee_status != "Left":
    #             frappe.throw(_("Employee relieved on {0} must be set as 'Left'").format(self.relieving_date))

    #     # payment_days = date_diff(self.actual_end_date, self.actual_start_date) + 1
    #     payment_days = 30

    #     if not cint(include_holidays_in_total_working_days):
    #         holidays = self.get_holidays_for_employee(self.actual_start_date, self.actual_end_date)
    #         payment_days -= len(holidays)

    #     return payment_days

    def get_amount_based_on_payment_days(self, row):
        amount, additional_amount = row.amount, row.additional_amount
        timesheet_component = self._salary_structure_doc.salary_component

        if (
            self.salary_structure
            and cint(row.depends_on_payment_days)
            and cint(self.total_working_days)
            and not (
                row.additional_salary and row.amount
            )  # to identify overwritten additional salary
            and (
                row.salary_component != timesheet_component
                or getdate(self.start_date) < self.joining_date
                or (self.relieving_date and getdate(self.end_date) > self.relieving_date)
            )
        ):
            additional_amount = flt(
                (flt(row.additional_amount) * flt(self.payment_days) / cint(self.total_working_days)),
                row.precision("additional_amount"),
            )
            amount = (
                flt(
                    (flt(row.amount) * flt(self.payment_days) / cint(self.total_working_days)),
                    row.precision("amount"),
                )
                + additional_amount
            )

        elif (
            not self.payment_days
            and row.salary_component != timesheet_component
            and cint(row.depends_on_payment_days)
        ):
            amount, additional_amount = 0, 0
        elif not row.amount:
            amount = flt(row.amount) + flt(row.additional_amount)

        # apply rounding
        if frappe.db.get_value(
            "Salary Component", row.salary_component, "round_to_the_nearest_integer", cache=True
        ):
            amount, additional_amount = rounded(amount or 0), rounded(additional_amount or 0)
        return amount, additional_amount
    @frappe.whitelist()
    def calculate_custom_cost_to_company_ctc(self) :
        
        custom_fields = frappe.db.get_all("Custom Field" , {
                "dt" :["in" , [ "Salary Slip" , "Salary Component"] ] ,
                "fieldname" : ["in" , ["custom_cost_to_company_ctc" , "custom_is_ctc_component"]]
            },
            pluck="name"
        )
        if len(custom_fields) == 2 :
            
            ctc_componenet = frappe.db.get_all("Salary Component" , {"custom_is_ctc_component" : 1} , pluck="name")           
            self.custom_cost_to_company_ctc = sum(map(lambda x : x.get("amount" , 0) if x.get("salary_component") in ctc_componenet  else 0 , self.earnings)) + self.net_pay
            # print(sum(map(lambda x : x.get("amount" , 0) if x.get("salary_component") in ctc_componenet  else 0 , self.earnings)))
            # print(self.custom_is_ctc_component)