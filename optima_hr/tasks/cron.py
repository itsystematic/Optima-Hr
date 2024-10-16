import frappe
from frappe import _
from datetime import timedelta
from erpnext import get_default_company
from frappe.utils import getdate, get_datetime
from hrms.hr.doctype.attendance.attendance import get_unmarked_days
from hrms.hr.doctype.shift_assignment.shift_assignment import get_shifts_for_date

@frappe.whitelist()
def make_attendance_absent_for_unmarked_employee(from_date, to_date):

    employess = get_employees_has_unmarked_days()

    for employee in employess :
        unmarked_days = get_unmarked_days(
            employee.get("employee") ,
            getdate(str(getdate() - timedelta(days=10)) ),
            getdate(),
            1
        )

        if not unmarked_days :
            continue

        for date in unmarked_days:
            date = get_datetime(date)
            e = employee.get("employee")

            shifts = get_shifts_for_date(e, date) # fetch all shifts for given employee and date

            if shifts:
                # shift_found = False
                for shift in shifts:
                    start_date = get_datetime(shift.start_date)
                    end_date = get_datetime(shift.end_date)
                    if start_date.date() <= date.date() <= end_date.date():  # Check if date falls within shift's start and end dates
                        shift_name = shift.shift_type
                        mark_bulk_attendance({
                            "employee" : employee.get("employee") ,
                            "unmarked_days" : [date.strftime("%Y-%m-%d")],  # Convert date to string
                            "status" : "Absent",
                            "company" : get_default_company(),
                            "shift": shift_name,
                        })
                        # shift_found = True
                        # break  # Exit the loop once the matching shift is found
                # if not shift_found:
                #     raise ValueError(f"No shift found for employee {e} on date {date.date()}")
            else:
                # shift type should be mandatory, otherwise raise an error
                return ValueError(f"No shifts found for employee {e} on date {date.date()}")
            
    return "Attendance marked as 'Absent' for employees with unmarked days."

def get_employees_has_unmarked_days() :
    
    return frappe.db.sql("""
        SELECT
            se.employee
        FROM `tabSet Employee Absent` se
        LEFT JOIN `tabEmployee` e
            ON e.name = se.employee
        WHERE e.status = 'Active'
        
    """,as_dict=1)
    

def mark_bulk_attendance(data):
	import json

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return

	for date in data.unmarked_days:
		doc_dict = {
			"doctype": "Attendance",
			"employee": data.employee,
			"attendance_date": get_datetime(date),
			"status": data.status,
            "shift": data.shift,  # Add this line
		}
		attendance = frappe.get_doc(doc_dict).insert()
		attendance.submit()