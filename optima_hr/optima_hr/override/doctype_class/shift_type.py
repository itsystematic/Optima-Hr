import frappe
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from itertools import groupby
from frappe.utils import cint, create_batch
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from datetime import timedelta
from optima_hr import get_company_setting_with_employee


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

        logs = self.get_employee_checkins()

        for key, group in groupby(logs, key=lambda x: (x["employee"], x["shift_start"])):
            single_shift_logs = list(group)
            attendance_date = key[1].date()
            employee = key[0]

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
        
        skip_employee = self.get_skip_employee_from_attendance()
        assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)
        
        for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
            for employee in batch :
                if employee in skip_employee :
                    continue
                
                self.mark_absent_for_dates_with_no_attendance(employee)

            frappe.db.commit()  # nosemgrep
        
            
    def get_employee_checkins(self) -> list[dict]:

        filters = { "skip_auto_attendance": 0,
            "attendance": ["is", "not set"],
            "time": [">=", self.process_attendance_after],
            "shift_actual_end": ["<", self.last_sync_of_checkin],
            "shift": self.name,
        }
        
        skip_employee = self.get_skip_employee_from_attendance()
        
        if skip_employee :
            filters.update({"employee" : ["not in" , skip_employee]})
        
        
        check_in = frappe.get_all(
            "Employee Checkin",
            fields=[
                "name",
                "employee",
                "log_type",
                "time",
                "shift",
                "shift_start",
                "shift_end",
                "shift_actual_start",
                "shift_actual_end",
                "device_id",
            ],
            filters=filters,
            order_by="employee,time",
        )

        return check_in


    def get_skip_employee_from_attendance(self) :
        
        return frappe.db.get_all("Skip Employee In Attendance" ,
        {"parent" : "HR Ensan Setting" , "parentfield" : "skip_employee_in_attendance" } , pluck="employee" )