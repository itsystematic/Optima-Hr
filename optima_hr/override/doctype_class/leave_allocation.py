import frappe
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation
from optima_hr.optima_hr.utils import custom_get_monthly_earned_leave

class OptimaLeaveAllocation(LeaveAllocation):

	@frappe.whitelist()
	def get_monthly_earned_leave(self):
		doj = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		annual_allocation = frappe.db.get_value(
			"Leave Policy Detail",
			{
				"parent": self.leave_policy,
				"leave_type": self.leave_type,
			},
			"annual_allocation",
		)

		frequency, rounding = frappe.db.get_value(
			"Leave Type",
			self.leave_type,
			[
				"earned_leave_frequency",
				"rounding",
			],
		)

		return custom_get_monthly_earned_leave(doj, annual_allocation, frequency, rounding)