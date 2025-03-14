
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip, set_loan_repayment, get_period_factor , get_salary_component_data
import frappe
from frappe import _
from frappe.utils import flt , cint , getdate,add_days  ,rounded,date_diff
from optima_hr.optima_hr.utils import allow_edit_salary_slip


class CustomSalarySlip(SalarySlip):
    
    @allow_edit_salary_slip
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

        self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
        self.base_gross_pay = flt(
            flt(self.gross_pay) * flt(self.exchange_rate), self.precision("base_gross_pay")
        )

        if self.salary_structure and self.is_new() :
            self.calculate_component_amounts("deductions")

        if self.get("loans") :
            
            set_loan_repayment(self)
        
        self.set_precision_for_component_amounts()
        self.set_net_pay()
        self.compute_income_tax_breakup()
        self.calculate_custom_cost_to_company_ctc()

    # @allow_edit_salary_slip
    def get_working_days_details(self, lwp=None, for_preview=0):
        payroll_settings = frappe.get_cached_value(
            "Payroll Settings",
            None,
            (
                "payroll_based_on",
                "include_holidays_in_total_working_days",
                "consider_marked_attendance_on_holidays",
                "daily_wages_fraction_for_half_day",
                "consider_unmarked_attendance_as",
            ),
            as_dict=1,
        )

        consider_marked_attendance_on_holidays = (
            payroll_settings.include_holidays_in_total_working_days
            and payroll_settings.consider_marked_attendance_on_holidays
        )

        daily_wages_fraction_for_half_day = (
            flt(payroll_settings.daily_wages_fraction_for_half_day) or 0.5
        )

        working_days = 30
        # working_days = date_diff(self.end_date, self.start_date) + 1
        if for_preview:
            self.total_working_days = working_days
            self.payment_days = working_days
            return

        holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
        working_days_list = [
            add_days(getdate(self.start_date), days=day) for day in range(0, working_days)
        ]

        if not cint(payroll_settings.include_holidays_in_total_working_days):
            working_days_list = [i for i in working_days_list if i not in holidays]

            # working_days -= len(holidays)
            working_days = 30
            if working_days < 0:
                frappe.throw(_("There are more holidays than working days this month."))

        if not payroll_settings.payroll_based_on:
            frappe.throw(_("Please set Payroll based on in Payroll settings"))

        if payroll_settings.payroll_based_on == "Attendance":
            actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(
                holidays, daily_wages_fraction_for_half_day, consider_marked_attendance_on_holidays
            )
            self.absent_days = absent
        else:
            actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(
                holidays, working_days_list, daily_wages_fraction_for_half_day
            )

        if not lwp:
            lwp = actual_lwp
        elif lwp != actual_lwp:
            frappe.msgprint(
                _("Leave Without Pay does not match with approved {} records").format(
                    payroll_settings.payroll_based_on
                )
            )

        self.leave_without_pay = lwp
        self.total_working_days = working_days

        payment_days = self.get_payment_days(payroll_settings.include_holidays_in_total_working_days)

        if flt(payment_days) > flt(lwp):
            self.payment_days = flt(payment_days) - flt(lwp)

            if payroll_settings.payroll_based_on == "Attendance":
                self.payment_days -= flt(absent)

            consider_unmarked_attendance_as = payroll_settings.consider_unmarked_attendance_as or "Present"

            if (
                payroll_settings.payroll_based_on == "Attendance"
                and consider_unmarked_attendance_as == "Absent"
            ):
                unmarked_days = self.get_unmarked_days(payroll_settings.include_holidays_in_total_working_days)
                self.absent_days += unmarked_days  # will be treated as absent
                self.payment_days -= unmarked_days
        else:
            self.payment_days = 0  
    
    # @allow_edit_salary_slip
    def get_payment_days(self, include_holidays_in_total_working_days):
        if self.joining_date and self.joining_date > getdate(self.end_date):
            # employee joined after payroll date
            return 0

        if self.relieving_date:
            employee_status = frappe.db.get_value("Employee", self.employee, "status")
            if self.relieving_date < getdate(self.start_date) and employee_status != "Left":
                frappe.throw(_("Employee relieved on {0} must be set as 'Left'").format(self.relieving_date))

        # payment_days = date_diff(self.actual_end_date, self.actual_start_date) + 1
        payment_days = 30

        if not cint(include_holidays_in_total_working_days):
            holidays = self.get_holidays_for_employee(self.actual_start_date, self.actual_end_date)
            # payment_days -= len(holidays)
            payment_days = 30

        return payment_days

    
    @allow_edit_salary_slip
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
            # Calculate amount based on payment days
            amount = flt(
                (flt(row.amount) * flt(self.payment_days) / cint(self.total_working_days)),
                row.precision("amount")
            )
            
            # Only add additional_amount if it exists
            if flt(row.additional_amount):
                additional_amount = flt(
                    (flt(row.additional_amount) * flt(self.payment_days) / cint(self.total_working_days)),
                    row.precision("additional_amount")
                )
                amount += additional_amount

        elif (
            not self.payment_days
            and row.salary_component != timesheet_component
            and cint(row.depends_on_payment_days)
        ):
            amount, additional_amount = 0, 0
        elif not row.amount:
            amount = flt(additional_amount)

        # apply rounding
        if frappe.db.get_value(
            "Salary Component", row.salary_component, "round_to_the_nearest_integer", cache=True
        ):
            amount = rounded(amount or 0)
            additional_amount = rounded(additional_amount or 0)
        
        return amount, additional_amount
    
    @frappe.whitelist()
    @allow_edit_salary_slip
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

    def add_additional_salary_components(self, component_type):
            # Update Addtionaal Salary Remove Employee Advaance if Returned or Claimed Or Partly Claimed and Returned
            # Last aamount not constent but caalculaation 

        

        additional_salaries = get_additional_salaries(
            self.employee, self.start_date, self.end_date, component_type
        )

        for additional_salary in additional_salaries:
            total_amount = additional_salary.amount
            if additional_salary.ref_doctype == "Employee Advance" :
                employee_advance = frappe.get_doc("Employee Advance" , additional_salary.ref_docname )
                total_receieved_amount = employee_advance.paid_amount - ( employee_advance.return_amount + employee_advance.claimed_amount )
                if additional_salary.amount > total_receieved_amount :
                    total_amount = total_receieved_amount


            self.update_component_row(
                get_salary_component_data(additional_salary.component),
                total_amount,
                component_type,
                additional_salary,
                is_recurring=additional_salary.is_recurring,
            )



def get_additional_salaries(employee, start_date, end_date, component_type):
	from frappe.query_builder import Criterion

	comp_type = "Earning" if component_type == "earnings" else "Deduction"

	additional_sal = frappe.qb.DocType("Additional Salary")
	component_field = additional_sal.salary_component.as_("component")
	overwrite_field = additional_sal.overwrite_salary_structure_amount.as_("overwrite")
	returned_employee_advance = frappe.db.get_all("Employee Advance", {"employee": employee , "docstatus" : 1 , "status" : ["in", ["Returned", "Claimed" , "Partly Claimed and Returned" ]]} , pluck="name") + ["leave"]

	additional_salary_list = (
		frappe.qb.from_(additional_sal)
		.select(
			additional_sal.name,
			component_field,
			additional_sal.type,
			additional_sal.amount,
			additional_sal.is_recurring,
			overwrite_field,
			additional_sal.deduct_full_tax_on_selected_payroll_date,
			additional_sal.ref_docname ,
			additional_sal.ref_doctype
		)
		.where(
			(additional_sal.employee == employee)
			& (additional_sal.docstatus == 1)
			& (additional_sal.type == comp_type)
			& (additional_sal.disabled == 0)
			& ~(additional_sal.ref_docname.isin(returned_employee_advance))
		)
		.where(
			Criterion.any(
				[
					Criterion.all(
						[  # is recurring and additional salary dates fall within the payroll period
							additional_sal.is_recurring == 1,
							additional_sal.from_date <= end_date,
							additional_sal.to_date >= end_date,
						]
					),
					Criterion.all(
						[  # is not recurring and additional salary's payroll date falls within the payroll period
							additional_sal.is_recurring == 0,
							additional_sal.payroll_date[start_date:end_date],
						]
					),
				]
			)
		)
		.run(as_dict=True)
	)

	additional_salaries = []
	components_to_overwrite = []

	for d in additional_salary_list:
		if d.overwrite:
			if d.component in components_to_overwrite:
				frappe.throw(
					_(
						"Multiple Additional Salaries with overwrite property exist for Salary Component {0} between {1} and {2}."
					).format(frappe.bold(d.component), start_date, end_date),
					title=_("Error"),
				)

			components_to_overwrite.append(d.component)

		additional_salaries.append(d)

	return additional_salaries
