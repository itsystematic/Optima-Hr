


import frappe
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import ( 
    LeavePolicyAssignment ,
    is_earned_leave_applicable_for_current_month ,
)

from frappe.utils import ( 
    getdate ,
    get_first_day ,
    get_last_day , 
    add_months ,
    date_diff ,

) 

from optima_hr.optima_hr.utils import custom_get_monthly_earned_leave

# Add Feature To Leave Policy Assignment 
# Add Daily Frequency

class OptimaHRLeavePolicyAssignment(LeavePolicyAssignment) :
    
	def get_leaves_for_passed_months(self, annual_allocation, leave_details, date_of_joining):
		def _get_current_and_from_date():
			current_date = frappe.flags.current_date or getdate()
			if current_date > getdate(self.effective_to):
				current_date = getdate(self.effective_to)

			from_date = getdate(self.effective_from)
			if getdate(date_of_joining) > from_date:
				from_date = getdate(date_of_joining)

			return current_date, from_date

		def _get_months_passed(current_date, from_date, consider_current_month):
			months_passed = 0
			if current_date.year == from_date.year and current_date.month >= from_date.month:
				months_passed = current_date.month - from_date.month
				if consider_current_month:
					months_passed += 1

			elif current_date.year > from_date.year:
				months_passed = (12 - from_date.month) + current_date.month
				if consider_current_month:
					months_passed += 1

			return months_passed

		def _get_pro_rata_period_end_date(consider_current_month):
			# for earned leave, pro-rata period ends on the last day of the month
			date = getdate(frappe.flags.current_date) or getdate()
			if consider_current_month:
				period_end_date = get_last_day(date)
			else:
				period_end_date = get_last_day(add_months(date, -1))

			return period_end_date

		def _calculate_leaves_for_passed_months(consider_current_month):
			monthly_earned_leave = custom_get_monthly_earned_leave(
				date_of_joining,
				annual_allocation,
				leave_details.earned_leave_frequency,
				leave_details.rounding,
				pro_rated=False,
			)
			period_end_date = _get_pro_rata_period_end_date(consider_current_month)
			if self.effective_from < date_of_joining <= period_end_date:
				# if the employee joined within the allocation period in some previous month,
				# calculate pro-rated leave for that month
				# and normal monthly earned leave for remaining passed months
				leaves = custom_get_monthly_earned_leave(
					date_of_joining,
					annual_allocation,
					leave_details.earned_leave_frequency,
					leave_details.rounding,
					get_first_day(date_of_joining),
					get_last_day(date_of_joining),
				)
				leaves += monthly_earned_leave * (months_passed - 1)
			else:
				leaves = monthly_earned_leave * months_passed

			return leaves

		consider_current_month = is_earned_leave_applicable_for_current_month(
			date_of_joining, leave_details.allocate_on_day
		)
		current_date, from_date = _get_current_and_from_date()
		months_passed_number = _get_months_passed(current_date, from_date, consider_current_month)

		months_passed = date_diff(getdate()  , self.effective_from ) if  leave_details.earned_leave_frequency == "Daily"  else months_passed_number

		if months_passed > 0:
			new_leaves_allocated = _calculate_leaves_for_passed_months(consider_current_month)
		else:
			new_leaves_allocated = 0

		return new_leaves_allocated
