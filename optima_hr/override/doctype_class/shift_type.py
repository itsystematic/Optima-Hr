import frappe
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from itertools import groupby
from frappe.utils import cint, create_batch
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
# from optima_hr.optima_hr.utils import get_company_setting_with_employee


EMPLOYEE_CHUNK_SIZE = 50


class OptimaShiftType(ShiftType) :

    

    """
    Override the get_employee_checkins method of ShiftType
    """
    
    
    @frappe.whitelist()
    def process_auto_attendance(self):

        if (
            not cint(self.enable_auto_attendance)
            or not self.process_attendance_after
            or not self.last_sync_of_checkin
        ):
            return

        skip_employee = get_skip_employees()
        logs = self.get_employee_checkins(skip_employee)

        for key, group in groupby(logs, key=lambda x: (x["employee"], x["shift_start"])):
            employee = key[0]
            attendance_date = key[1].date()
            single_shift_logs = list(group)

            if not self.should_mark_attendance(employee, attendance_date):
                continue

            (
                attendance_status,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
            ) = self.get_attendance(single_shift_logs)

            mark_attendance_and_link_log(
                single_shift_logs,
                attendance_status,
                attendance_date,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
                self.name,
            )
            
        frappe.db.commit() 
        
        assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)
        
        for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
            for employee in batch :
                if employee in skip_employee :
                    continue
                
                self.mark_absent_for_dates_with_no_attendance(employee)

            frappe.db.commit()  # nosemgrep
        
            
    def get_employee_checkins(self , skip_employee=None) -> list[dict]:
        
        employee = frappe.qb.DocType("Employee")
        check_in = frappe.qb.DocType("Employee Checkin")

        query = (
            frappe.qb.from_(check_in)
            .left_join(employee)
            .on(employee.name == check_in.employee)
            .select(
                check_in.name,
                check_in.employee,
                employee.company ,
                check_in.log_type,
                check_in.time,
                check_in.shift,
                check_in.shift_start,
                check_in.shift_end,
                check_in.shift_actual_start,
                check_in.shift_actual_end,
                check_in.device_id,
            )
            .where(check_in.skip_auto_attendance == 0)
            .where(check_in.attendance.isnull())
            .where(check_in.time >= self.process_attendance_after)
            .where(check_in.shift_actual_end < self.last_sync_of_checkin)
            .where(check_in.shift == self.name)
        )

        if skip_employee :
            query = query.where(~employee.name.isin(skip_employee))

        return query.run(as_dict=True)


def get_skip_employees() :

    return frappe.db.sql("""

        SELECT se.employee
        FROM `tabOptima Hr Setting` ohs
        INNER JOIN `tabSet Employee Absent` se
        WHERE ohs.skip_employee = 1
    """ ,pluck=True)