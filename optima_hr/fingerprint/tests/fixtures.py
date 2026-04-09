"""
Test Fixtures for Performance Testing

Provides utilities to generate realistic test data:
- Employees
- Shift Types
- Machine Logs
- Shift Assignments
- Cleanup utilities
"""

import frappe
import random
from datetime import datetime, timedelta
from frappe.utils import get_datetime, getdate, now_datetime


# Test data prefixes to identify and clean up test records
TEST_PREFIX = "PERFTEST"
TEST_EMPLOYEE_PREFIX = f"{TEST_PREFIX}_EMP"
TEST_SHIFT_PREFIX = f"{TEST_PREFIX}_SHIFT"
TEST_DEVICE_PREFIX = f"{TEST_PREFIX}_DEVICE"


def create_test_employees(count=10):
    """
    Create test Employee records

    Args:
        count: Number of employees to create

    Returns:
        list: List of created employee names
    """
    employees = []

    for i in range(count):
        emp_id = f"{TEST_EMPLOYEE_PREFIX}_{i+1:04d}"

        # Check if already exists
        if frappe.db.exists("Employee", emp_id):
            employees.append(emp_id)
            continue

        try:
            emp = frappe.new_doc("Employee")
            emp.name = emp_id
            emp.employee = emp_id
            emp.employee_name = f"Test Employee {i+1}"
            emp.first_name = f"Test{i+1}"
            emp.status = "Active"
            emp.gender = random.choice(["Male", "Female"])
            emp.date_of_birth = datetime(1990, 1, 1) + timedelta(days=random.randint(0, 10000))
            emp.date_of_joining = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1000))

            # Set attendance device ID (used for matching machine logs)
            emp.attendance_device_id = str(1000 + i)

            emp.flags.ignore_permissions = True
            emp.flags.ignore_mandatory = True
            emp.insert()

            employees.append(emp.name)

        except Exception as e:
            frappe.log_error(f"Error creating test employee {emp_id}: {str(e)}")

    frappe.db.commit()
    return employees


def create_test_shifts(count=5):
    """
    Create test Shift Type records

    Args:
        count: Number of shifts to create

    Returns:
        list: List of created shift names
    """
    shifts = []

    for i in range(count):
        shift_id = f"{TEST_SHIFT_PREFIX}_{i+1:02d}"

        # Check if already exists
        if frappe.db.exists("Shift Type", shift_id):
            shifts.append(shift_id)
            continue

        try:
            shift = frappe.new_doc("Shift Type")
            shift.name = shift_id
            shift.shift_type = shift_id

            # Set realistic shift times
            start_hour = 8 + (i * 2)  # Stagger shifts
            shift.start_time = f"{start_hour:02d}:00:00"
            shift.end_time = f"{(start_hour + 8) % 24:02d}:00:00"

            shift.enable_auto_attendance = 1

            shift.flags.ignore_permissions = True
            shift.insert()

            shifts.append(shift.name)

        except Exception as e:
            frappe.log_error(f"Error creating test shift {shift_id}: {str(e)}")

    frappe.db.commit()
    return shifts


def create_test_devices(count=3):
    """
    Create test Fingerprint Machine records

    Args:
        count: Number of devices to create

    Returns:
        list: List of created device IDs
    """
    devices = []

    for i in range(count):
        device_id = f"{TEST_DEVICE_PREFIX}_{i+1:02d}"

        # Check if already exists
        if frappe.db.exists("Fingerprint Machine", device_id):
            devices.append(device_id)
            continue

        try:
            device = frappe.new_doc("Fingerprint Machine")
            device.device_id = device_id
            device.machine_name = f"Test Device {i+1}"
            device.location = f"Test Location {i+1}"

            device.flags.ignore_permissions = True
            device.flags.ignore_mandatory = True
            device.insert()

            devices.append(device.device_id)

        except Exception as e:
            frappe.log_error(f"Error creating test device {device_id}: {str(e)}")

    frappe.db.commit()
    return devices


def create_test_machine_logs(count, employees=None, shifts=None, devices=None, base_date=None):
    """
    Create test Machine Log records

    Args:
        count: Number of machine logs to create
        employees: List of employee names (auto-created if None)
        shifts: List of shift names (not directly used, but for context)
        devices: List of device IDs (auto-created if None)
        base_date: Base datetime for logs (defaults to now)

    Returns:
        list: List of created machine log names

    Data distribution:
    - 70% normal checkins (IN/OUT pairs)
    - 20% single checkins (only IN or OUT)
    - 10% duplicates (for duplicate detection testing)
    """
    if employees is None:
        employees = create_test_employees(min(10, count // 10))

    if devices is None:
        devices = create_test_devices(3)

    if base_date is None:
        base_date = now_datetime()

    logs_created = []
    duplicate_candidates = []  # Track logs for duplication

    # Determine how many of each type
    normal_pairs = int(count * 0.70)
    single_checkins = int(count * 0.20)
    duplicates = count - normal_pairs - single_checkins

    log_count = 0

    # Create normal IN/OUT pairs
    for i in range(normal_pairs // 2):
        employee = random.choice(employees)
        device = random.choice(devices)

        # Get employee's attendance device ID
        enroll_no = frappe.db.get_value("Employee", employee, "attendance_device_id")

        if not enroll_no:
            continue

        # Random time during the day (spread across 8 hours)
        time_offset_in = timedelta(
            minutes=random.randint(0, 480)  # 8 hours in minutes
        )

        time_offset_out = time_offset_in + timedelta(
            hours=random.randint(7, 9),  # Work 7-9 hours
            minutes=random.randint(0, 59)
        )

        # Create IN log
        log_in = _create_machine_log(
            enroll_no=enroll_no,
            timestamp=base_date + time_offset_in,
            device=device,
            punch_code=0,  # IN
            employee=employee
        )

        if log_in:
            logs_created.append(log_in)
            duplicate_candidates.append(log_in)
            log_count += 1

        # Create OUT log
        log_out = _create_machine_log(
            enroll_no=enroll_no,
            timestamp=base_date + time_offset_out,
            device=device,
            punch_code=1,  # OUT
            employee=employee
        )

        if log_out:
            logs_created.append(log_out)
            duplicate_candidates.append(log_out)
            log_count += 1

    # Create single checkins
    for i in range(single_checkins):
        employee = random.choice(employees)
        device = random.choice(devices)

        enroll_no = frappe.db.get_value("Employee", employee, "attendance_device_id")

        if not enroll_no:
            continue

        time_offset = timedelta(minutes=random.randint(0, 480))

        log = _create_machine_log(
            enroll_no=enroll_no,
            timestamp=base_date + time_offset,
            device=device,
            punch_code=random.choice([0, 1]),  # Random IN or OUT
            employee=employee
        )

        if log:
            logs_created.append(log)
            duplicate_candidates.append(log)
            log_count += 1

    # Create duplicates (copy some existing logs)
    for i in range(min(duplicates, len(duplicate_candidates))):
        source_log_name = random.choice(duplicate_candidates)

        # Get source log data
        source_log = frappe.get_doc("Machine Log", source_log_name)

        # Create duplicate with same data
        duplicate = _create_machine_log(
            enroll_no=source_log.enroll_no,
            timestamp=source_log.time,
            device=source_log.device,
            punch_code=source_log.punch,
            employee=source_log.employee,
            force_unique=True  # Force creation even if duplicate
        )

        if duplicate:
            logs_created.append(duplicate)
            log_count += 1

    frappe.db.commit()
    return logs_created


def _create_machine_log(enroll_no, timestamp, device, punch_code, employee, force_unique=False):
    """
    Internal helper to create a single Machine Log

    Args:
        enroll_no: Employee enrollment number
        timestamp: Log timestamp
        device: Device ID
        punch_code: Punch code (0=IN, 1=OUT)
        employee: Employee name
        force_unique: Force creation even if duplicate

    Returns:
        str: Created log name or None
    """
    try:
        # Generate a unique ID
        import hashlib
        import uuid

        if force_unique:
            # Add random component for forced duplicates
            data_string = f"{enroll_no}_{timestamp}_{device}_{punch_code}_{uuid.uuid4()}"
        else:
            data_string = f"{enroll_no}_{timestamp}_{device}_{punch_code}"

        log_id = hashlib.md5(data_string.encode()).hexdigest()[:16].upper()

        # Check if already exists
        if not force_unique and frappe.db.exists("Machine Log", {"id": log_id}):
            return None

        log = frappe.new_doc("Machine Log")
        log.id = log_id
        log.enroll_no = str(enroll_no)
        log.time = get_datetime(timestamp)
        log.date = getdate(timestamp)
        log.device = device
        log.punch = str(punch_code)
        log.employee = employee
        log.employee_check_in_created = 0

        # Determine type based on punch code
        if int(punch_code) in [0, 4]:
            log.type = "IN"
        elif int(punch_code) in [1, 5]:
            log.type = "OUT"

        log.flags.ignore_permissions = True
        log.insert()

        return log.name

    except Exception as e:
        frappe.log_error(f"Error creating machine log: {str(e)}")
        return None


def create_shift_assignments(employees, shifts, base_date=None):
    """
    Assign employees to shifts

    Args:
        employees: List of employee names
        shifts: List of shift names
        base_date: Base date for assignments (defaults to now)

    Returns:
        list: List of created shift assignment names
    """
    if base_date is None:
        base_date = getdate()

    assignments = []

    for employee in employees:
        shift = random.choice(shifts)

        # Check if assignment already exists
        existing = frappe.db.exists("Shift Assignment", {
            "employee": employee,
            "shift_type": shift,
            "start_date": base_date
        })

        if existing:
            assignments.append(existing)
            continue

        try:
            assignment = frappe.new_doc("Shift Assignment")
            assignment.employee = employee
            assignment.shift_type = shift
            assignment.start_date = base_date
            assignment.status = "Active"

            assignment.flags.ignore_permissions = True
            assignment.insert()

            assignments.append(assignment.name)

        except Exception as e:
            frappe.log_error(f"Error creating shift assignment for {employee}: {str(e)}")

    frappe.db.commit()
    return assignments


def cleanup_test_data():
    """
    Clean up all test data created by this module

    Deletes:
    - Test Machine Logs
    - Test Employee Checkins (created from test logs)
    - Test Shift Assignments
    - Test Employees
    - Test Shifts
    - Test Devices
    """
    try:
        # Delete in reverse dependency order

        # 1. Delete Machine Logs
        frappe.db.sql("""
            DELETE FROM `tabMachine Log`
            WHERE device LIKE %s
        """, (f"{TEST_DEVICE_PREFIX}%",))

        # 2. Delete Employee Checkins (created from test employees)
        frappe.db.sql("""
            DELETE FROM `tabEmployee Checkin`
            WHERE employee LIKE %s
        """, (f"{TEST_EMPLOYEE_PREFIX}%",))

        # 3. Delete Shift Assignments
        frappe.db.sql("""
            DELETE FROM `tabShift Assignment`
            WHERE employee LIKE %s
        """, (f"{TEST_EMPLOYEE_PREFIX}%",))

        # 4. Delete Employees
        frappe.db.sql("""
            DELETE FROM `tabEmployee`
            WHERE name LIKE %s
        """, (f"{TEST_EMPLOYEE_PREFIX}%",))

        # 5. Delete Shift Types
        frappe.db.sql("""
            DELETE FROM `tabShift Type`
            WHERE name LIKE %s
        """, (f"{TEST_SHIFT_PREFIX}%",))

        # 6. Delete Fingerprint Machines
        frappe.db.sql("""
            DELETE FROM `tabFingerprint Machine`
            WHERE device_id LIKE %s
        """, (f"{TEST_DEVICE_PREFIX}%",))

        frappe.db.commit()

        print(f"[CLEANUP] Successfully cleaned up all test data with prefix: {TEST_PREFIX}")

    except Exception as e:
        frappe.log_error(f"Error cleaning up test data: {str(e)}")
        frappe.db.rollback()
        raise


def get_test_data_stats():
    """
    Get statistics about existing test data

    Returns:
        dict: Counts of test records
    """
    return {
        'employees': frappe.db.count("Employee", {"name": ["like", f"{TEST_EMPLOYEE_PREFIX}%"]}),
        'shifts': frappe.db.count("Shift Type", {"name": ["like", f"{TEST_SHIFT_PREFIX}%"]}),
        'devices': frappe.db.count("Fingerprint Machine", {"device_id": ["like", f"{TEST_DEVICE_PREFIX}%"]}),
        'machine_logs': frappe.db.count("Machine Log", {"device": ["like", f"{TEST_DEVICE_PREFIX}%"]}),
        'employee_checkins': frappe.db.count("Employee Checkin", {"employee": ["like", f"{TEST_EMPLOYEE_PREFIX}%"]}),
        'shift_assignments': frappe.db.count("Shift Assignment", {"employee": ["like", f"{TEST_EMPLOYEE_PREFIX}%"]})
    }


def setup_complete_test_environment(n_employees=20, n_shifts=5, n_devices=3):
    """
    Setup a complete test environment with all required data

    Args:
        n_employees: Number of employees to create
        n_shifts: Number of shifts to create
        n_devices: Number of devices to create

    Returns:
        dict: Created data references
    """
    print(f"[SETUP] Creating test environment...")

    employees = create_test_employees(n_employees)
    print(f"[SETUP] Created {len(employees)} employees")

    shifts = create_test_shifts(n_shifts)
    print(f"[SETUP] Created {len(shifts)} shifts")

    devices = create_test_devices(n_devices)
    print(f"[SETUP] Created {len(devices)} devices")

    assignments = create_shift_assignments(employees, shifts)
    print(f"[SETUP] Created {len(assignments)} shift assignments")

    return {
        'employees': employees,
        'shifts': shifts,
        'devices': devices,
        'assignments': assignments
    }
