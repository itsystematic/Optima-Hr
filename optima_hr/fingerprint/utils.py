import frappe
import json
import hashlib
from frappe import _ 
from frappe.utils import get_datetime, getdate 

@frappe.whitelist()
def create_machine_log(
    enroll_no,
    timestamp,
    device_id,
    punch_code,
    batch_id=None,
    force_create=False
):
    """
    Create Machine Log entry - primary endpoint for device integration
    
    :param enroll_no: Employee enrollment number from device
    :param timestamp: Raw timestamp from device
    :param device_id: Device identifier
    :param punch_code: Raw punch code from device
    :param batch_id: Optional batch identifier for bulk operations
    :param force_create: Skip duplicate checks if True
    :return: Dict with status and created log details
    """
    try:
        # Generate unique ID for this log entry
        log_id = _generate_machine_log_id(enroll_no, timestamp, device_id, punch_code)
        
        # Check for duplicates unless forced
        if not force_create:
            existing_log = frappe.db.exists("Machine Log", {"id": log_id})
            if existing_log:
                return 200, {
                    "status": "success",
                    "message": "Log already exists",
                    "data": {"name": existing_log, "id": log_id},
                    "duplicate": True
                }
        
        # Parse timestamp
        parsed_time = get_datetime(timestamp)
        
        # Create Machine Log
        machine_log = frappe.new_doc("Machine Log")
        machine_log.id = log_id
        machine_log.enroll_no = str(enroll_no)
        machine_log.time = parsed_time
        machine_log.date = getdate(parsed_time)
        machine_log.device = device_id
        machine_log.punch = str(punch_code)
        machine_log.employee_check_in_created = 0
        
        # Try to resolve employee immediately (optional)
        employee = _resolve_employee_from_enroll_no(enroll_no)
        if employee:
            machine_log.employee = employee["name"]
            machine_log.type = _determine_punch_type(punch_code, device_id)
        
        # Set batch reference if provided
        if batch_id and hasattr(machine_log, 'batch_id'):
            machine_log.batch_id = batch_id
        
        machine_log.flags.ignore_permissions = True
        machine_log.insert()
        
        return 200,{
            "status": "success",
            "message": "Machine log created successfully",
            "data": {
                "name": machine_log.name,
                "id": machine_log.id,
                "employee_resolved": bool(employee)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating machine log: {str(e)}")
        return 500,{
            "status": "error",
            "message": str(e),
            "data": None
        }


@frappe.whitelist(allow_guest=True)
def create_bulk_machine_logs(logs_data):
    """
    Create multiple Machine Log entries in bulk
    
    :param logs_data: JSON array of log objects
    :return: Bulk operation results
    """
    try:
        logs = json.loads(logs_data) if isinstance(logs_data, str) else logs_data
        batch_id = frappe.generate_hash(length=12)
        
        results = {
            "batch_id": batch_id,
            "total_records": len(logs),
            "successful": 0,
            "duplicates": 0,
            "failed": 0,
            "results": []
        }
        
        # Process in batches for better performance
        batch_size = 100
        for i in range(0, len(logs), batch_size):
            batch_logs = logs[i:i + batch_size]
            
            for log_data in batch_logs:
                result = create_machine_log(
                    enroll_no=log_data.get("enroll_no"),
                    timestamp=log_data.get("timestamp"),
                    device_id=log_data.get("device_id"),
                    punch_code=log_data.get("punch_code"),
                    batch_id=batch_id,
                    force_create=False
                )
                
                results["results"].append(result)
                if result["status"] == "success":
                    if result.get("duplicate"):
                        results["duplicates"] += 1
                    else:
                        results["successful"] += 1
                else:
                    results["failed"] += 1
            
            # Commit after each batch
            frappe.db.commit()
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in bulk machine log creation: {str(e)}")
        return {
            "status": "error",
            "message": f"Bulk operation failed: {str(e)}"
        }


def _generate_machine_log_id(enroll_no, timestamp, device_id, punch_code):
    """Generate unique ID for machine log"""
    data_string = f"{enroll_no}_{timestamp}_{device_id}_{punch_code}"
    return hashlib.md5(data_string.encode()).hexdigest()[:16].upper()


def _resolve_employee_from_enroll_no(enroll_no):
    """Resolve employee from enrollment number with device context"""
    try:
        # Primary lookup by attendance_device_id
        employee = frappe.db.get_value(
            "Employee",
            {"attendance_device_id": enroll_no, "status": "Active"},
            ["name", "employee_name"],
            as_dict=True
        )
        
        return employee
        
    except Exception:
        return None


def _determine_punch_type(punch_code, device_id=None):
    """Determine IN/OUT from punch code with device-specific logic"""
    # Get device-specific configuration
    device_config = _get_device_config(device_id)
    
    punch_code = int(punch_code) if str(punch_code).isdigit() else punch_code
    
    if device_config:
        if punch_code in device_config.get("in_punch_codes", [0, 4]):
            return "IN"
        elif punch_code in device_config.get("out_punch_codes", [1, 5]):
            return "OUT"
    
    # Default logic
    if punch_code in [0, 4]:
        return "IN"
    elif punch_code in [1, 5]:
        return "OUT"
    
    return None


def _get_device_config(device_id):
    """Get device-specific configuration"""
    if not device_id:
        return None
    
    try:
        device_doc = frappe.get_doc("Fingerprint Machine", device_id)
        return {
            "in_punch_codes": getattr(device_doc, "in_punch_codes", [0, 4]),
            "out_punch_codes": getattr(device_doc, "out_punch_codes", [1, 5])
        }
    except Exception:
        return None
    
    
@frappe.whitelist()
def create_employee_checkin():
    """Convert unprocessed Machine Log entries to Employee Checkin records."""
    limit_count = 200
    machine_logs = frappe.db.sql(
        """
        SELECT name, employee, time as timestamp, type as log_type, device
        FROM `tabMachine Log`
        WHERE employee IS NOT NULL AND employee_check_in_created = 0
        ORDER BY time ASC
        LIMIT %(limit)s
        """,
        {"limit": limit_count},
        as_dict=True,
    )

    if not machine_logs:
        return

    failed_logs = []
    processed_log_names = []
    shift_sync_updates = {}
    device_sync_updates = {}

    for log in machine_logs:
        try:
            employee = frappe.get_doc("Employee", log.employee)
            if frappe.db.get_value("Employee", employee.name, "status") != "Active":
                continue

            existing_checkin = frappe.db.exists(
                "Employee Checkin",
                {
                    "employee": log.employee,
                    "time": log.timestamp,
                    "log_type": log.log_type,
                },
            )

            if existing_checkin:
                processed_log_names.append(log.name)
                _track_device_last_sync(device_sync_updates, log.device, log.timestamp)

                existing_checkin_details = frappe.db.get_value(
                    "Employee Checkin",
                    existing_checkin,
                    ["shift", "shift_actual_end"],
                    as_dict=True,
                )
                if existing_checkin_details:
                    _track_shift_last_sync(
                        shift_sync_updates,
                        existing_checkin_details.shift,
                        existing_checkin_details.shift_actual_end,
                    )
                continue

            doc = frappe.new_doc("Employee Checkin")
            doc.employee = employee.name
            doc.employee_name = employee.employee_name
            doc.time = log.timestamp
            doc.device_id = log.device
            doc.log_type = log.log_type
            doc.latitude = None
            doc.longitude = None
            doc.skip_auto_attendance = 0

            doc.fetch_shift()
            doc.insert()

            processed_log_names.append(log.name)
            _track_device_last_sync(device_sync_updates, log.device, log.timestamp)
            _track_shift_last_sync(shift_sync_updates, doc.shift, doc.shift_actual_end)

        except Exception as e:
            failed_logs.append(f"[{log.name}] {str(e)}")

    if processed_log_names:
        frappe.db.sql(
            """
            UPDATE `tabMachine Log`
            SET employee_check_in_created = 1
            WHERE name IN ({})
            """.format(",".join(["%s"] * len(processed_log_names))),
            processed_log_names,
        )
        frappe.db.commit()

    _update_shift_last_syncs(shift_sync_updates)
    _update_fingerprint_machine_last_syncs(device_sync_updates)

    if failed_logs:
        frappe.log_error(
            title="Employee Checkin Creation Errors",
            message="Failed Logs:\n" + "\n".join(failed_logs),
        )


def _track_shift_last_sync(shift_sync_updates, shift_name, shift_actual_end):
    if not shift_name or not shift_actual_end:
        return

    new_sync_time = get_datetime(shift_actual_end) + timedelta(minutes=1)
    current_sync_time = shift_sync_updates.get(shift_name)

    if not current_sync_time or new_sync_time > current_sync_time:
        shift_sync_updates[shift_name] = new_sync_time


def _track_device_last_sync(device_sync_updates, device_id, timestamp):
    if not device_id or not timestamp:
        return

    sync_time = get_datetime(timestamp)
    current_sync_time = device_sync_updates.get(device_id)

    if not current_sync_time or sync_time > current_sync_time:
        device_sync_updates[device_id] = sync_time


def _update_shift_last_syncs(shift_sync_updates):
    for shift_name, max_timestamp in shift_sync_updates.items():
        try:
            current_last_sync = frappe.db.get_value("Shift Type", shift_name, "last_sync_of_checkin")
            if not current_last_sync or get_datetime(max_timestamp) > get_datetime(current_last_sync):
                frappe.db.set_value("Shift Type", shift_name, "last_sync_of_checkin", max_timestamp)
                frappe.logger().info(
                    f"[FINGERPRINT] Updated last sync for shift {shift_name} to {max_timestamp}"
                )
        except Exception as e:
            frappe.log_error(f"Error updating shift sync for {shift_name}: {str(e)}")


def _update_fingerprint_machine_last_syncs(device_sync_updates):
    for device_id, max_timestamp in device_sync_updates.items():
        try:
            current_last_sync = frappe.db.get_value("Fingerprint Machine", device_id, "last_sync")
            if not current_last_sync or get_datetime(max_timestamp) > get_datetime(current_last_sync):
                frappe.db.set_value("Fingerprint Machine", device_id, "last_sync", max_timestamp)
        except Exception as e:
            frappe.log_error(f"Error updating machine sync for {device_id}: {str(e)}")


@frappe.whitelist()
def update_lastsynced_recodrd_log_timestamp(device_id, last_synced_record_datetime):
    try:
        frappe.db.sql("""
        Update `tabFingerprint Machine` set last_synced_record_datetime = %s where device_id = %s
        """, (last_synced_record_datetime, device_id))

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            title="Error Updating Last Synced Record Timestamp",
            message=f"Device ID: {device_id}, Error: {str(e)}"
        )
        return 500, {
            "status": "error",
            "message": str(e)
        }
    
