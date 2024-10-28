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
    def process_auto_attendance(self , company=None):
        print("in in in ")
        skip_employee = []

        if (
            not cint(self.enable_auto_attendance)
            or not self.process_attendance_after
            or not self.last_sync_of_checkin
        ):
            return

        logs = self.get_employee_checkins(company)
        optima_hr_settings = get_optima_hr_settings(company)

        for key, group in groupby(logs, key=lambda x: (x["company"] ,x["employee"], x["shift_start"])):
            company = key[0]
            employee = key[1]
            attendance_date = key[2].date()
            single_shift_logs = list(group)

            if setting := optima_hr_settings.get("company") :
                skip_employee += list(map(lambda x : x.get("employee") , setting.skip_employee_in_attendance))

                if setting.get("skip_employee") and setting.get("skip_employee_date_range") :
                    if not (setting.get("skip_employee_from_date") <= attendance_date <= setting.get("skip_employee_to_date") ):
                        continue

            if not self.should_mark_attendance(employee, attendance_date) or employee in skip_employee :
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
        
            
    def get_employee_checkins(self , company=None) -> list[dict]:
        
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

        if company : query.where(employee.company == company)

        return query.run(as_dict=True)


    # def get_skip_employee_from_attendance(self , company=None) :

    #     filters = {"parentfield" : "skip_employee_in_attendance"}
    #     if company : filters["parent"] = company
    #     skip_employees = frappe.db.get_all("Set Employee Absent" ,filters , pluck="employee" )

    #     return skip_employees

def get_optima_hr_settings(company=None) :

    filters = {}
    optima_hr_settings = {}

    if company : filters["company"] = company

    for optima_hr in frappe.db.get_all("Optima HR Setting" , filters,pluck="name") :
        optima_hr_settings[optima_hr] = frappe.get_doc("Optima HR Setting" , optima_hr)

    return optima_hr_settings