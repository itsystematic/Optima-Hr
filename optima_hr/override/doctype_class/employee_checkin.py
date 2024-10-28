

import frappe
from frappe import _
from frappe.auth import get_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin, get_actual_start_end_datetime_of_shift

class CustomEmployeeCheckin(EmployeeCheckin):

    @frappe.whitelist()
    def fetch_shift(self):
        """
        This method overrides the method in employee_checkin
        To prevent returning None value for shift
        if NOt found always throw error message
        """
        if not (
            shift_actual_timings := get_actual_start_end_datetime_of_shift(
                self.employee, get_datetime(self.time), True
            )
        ):
            frappe.throw(_("No Shifts assigned for Employee: {0} in time: {1}") # if no shifts assigned, throw error
                .format(frappe.bold(self.employee), frappe.bold(self.time)))

            # self.shift = None
            # return

        if (
            shift_actual_timings.shift_type.determine_check_in_and_check_out
            == "Strictly based on Log Type in Employee Checkin"
            and not self.log_type
            and not self.skip_auto_attendance
        ):
            frappe.throw(
                _("Log Type is required for check-ins falling in the shift: {0}.").format(
                    shift_actual_timings.shift_type.name
                )
            )
        if not self.attendance:
            self.shift = shift_actual_timings.shift_type.name
            self.shift_actual_start = shift_actual_timings.actual_start
            self.shift_actual_end = shift_actual_timings.actual_end
            self.shift_start = shift_actual_timings.start_datetime
            self.shift_end = shift_actual_timings.end_datetime