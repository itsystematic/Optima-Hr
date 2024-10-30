import frappe

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee






# Custom
@frappe.whitelist()
def create_attendance(
    employee: str,
    company: str,
    attendance_date: str,
    status: str,
    shift_type: str
) -> str:
    try:
        # Create a new Attendance document
        attendance_doc = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "company": company,
            "attendance_date": attendance_date,
            "shift": shift_type,
            "status": status,
        })
        
        # Insert the document into the database
        attendance_doc.insert(ignore_permissions=True)

        # Optionally submit the document if needed
        attendance_doc.submit()

        # Return the name (ID) of the created attendance record
        return attendance_doc.name

    except frappe.exceptions.ValidationError as e:
        frappe.log_error(message=str(e), title="Attendance Creation Failed")
        frappe.throw(("Attendance creation failed: {0}").format(str(e)))
    except Exception as e:
        frappe.log_error(message=str(e), title="Unknown Error in Attendance Creation")
        frappe.throw(("An unknown error occurred: {0}").format(str(e)))
        
@frappe.whitelist()
def get_attendance(
    date_start: str, date_end: str, employee_filters: dict[str, str]
) -> dict[str, list[dict]]:
    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.select(
            Attendance.name,
            Attendance.employee,
            Attendance.attendance_date,
            Attendance.status,
        )
        .from_(Attendance)
        .left_join(Employee)
        .on(Attendance.employee == Employee.name)
        .where(
            (Attendance.attendance_date >= date_start)
            & (Attendance.attendance_date <= date_end)
            & (Attendance.docstatus == 1) 
            & (Employee.status == "Active") 
        )
    )

    for filter_key in employee_filters:
        query = query.where(Employee[filter_key] == employee_filters[filter_key])

    return group_by_employee(query.run(as_dict=True))

def group_by_employee(events: list[dict]) -> dict[str, list[dict]]:
    grouped_events = {}
    for event in events:
        grouped_events.setdefault(event["employee"], []).append(
            {k: v for k, v in event.items() if k != "employee"}
        )
    return grouped_events

@frappe.whitelist()
def clear_cache_and_get_csrf_token():
    frappe.clear_cache()

    csrf_token = frappe.sessions.get_csrf_token()

    return {"csrf_token": csrf_token}



# ROSTER
@frappe.whitelist()
def get_events(
	month_start: str, month_end: str, employee_filters: dict[str, str]
) -> dict[str, list[dict]]:
	holidays = get_holidays(month_start, month_end, employee_filters)
	leaves = get_leaves(month_start, month_end, employee_filters)
	attendances = get_attendance(month_start, month_end, employee_filters)

	events = {}
	for event in [holidays, leaves, attendances]:
		for key, value in event.items():
			if key in events:
				events[key].extend(value)
			else:
				events[key] = value
	return events


def get_holidays(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	holidays = {}

	for employee in frappe.get_list("Employee", filters=employee_filters, pluck="name"):
		if holiday_list := get_holiday_list_for_employee(employee, raise_exception=False):
			holidays[employee] = frappe.get_all(
				"Holiday",
				filters={"parent": holiday_list, "holiday_date": ["between", [month_start, month_end]]},
				fields=["name as holiday", "holiday_date", "description", "weekly_off"],
			)

	return holidays



def get_leaves(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	LeaveApplication = frappe.qb.DocType("Leave Application")
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.select(
			LeaveApplication.name.as_("leave"),
			LeaveApplication.employee,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		)
		.from_(LeaveApplication)
		.left_join(Employee)
		.on(LeaveApplication.employee == Employee.name)
		.where(
			(LeaveApplication.docstatus == 1)
			& (LeaveApplication.status == "Approved")
			& (LeaveApplication.from_date <= month_end)
			& (LeaveApplication.to_date >= month_start)
		)
	)

	for filter in employee_filters:
		query = query.where(Employee[filter] == employee_filters[filter])

	return group_by_employee(query.run(as_dict=True))
