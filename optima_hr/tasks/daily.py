import frappe 
from frappe.utils import getdate
from hrms.hr.utils import get_leave_allocations 
from optima_hr.optima_hr.utils import (
    custom_get_earned_leaves ,
    custom_check_effective_date ,
    custom_update_previous_leave_allocation ,
)

# Method To run daily at 12:01 AM To add Leaves to Employees
def daily_allocate_earned_leaves():
	"""Allocate earned leaves to Employees"""
	e_leave_types = custom_get_earned_leaves()
	today = frappe.flags.current_date or getdate()

	for e_leave_type in e_leave_types:
		leave_allocations = get_leave_allocations(today, e_leave_type.name)
		for allocation in leave_allocations:
			if not allocation.leave_policy_assignment and not allocation.leave_policy:
				continue

			leave_policy = (
				allocation.leave_policy
				if allocation.leave_policy
				else frappe.db.get_value(
					"Leave Policy Assignment", allocation.leave_policy_assignment, ["leave_policy"]
				)
			)

			annual_allocation = frappe.db.get_value(
				"Leave Policy Detail",
				filters={"parent": leave_policy, "leave_type": e_leave_type.name},
				fieldname=["annual_allocation"],
			)
			date_of_joining = frappe.db.get_value("Employee", allocation.employee, "date_of_joining")
			custom_update_previous_leave_allocation(allocation, annual_allocation, e_leave_type, date_of_joining)