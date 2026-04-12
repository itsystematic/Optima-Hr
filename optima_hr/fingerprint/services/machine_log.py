import hashlib
import json

import frappe
from frappe.utils import get_datetime, getdate


def create_machine_log(enroll_no, timestamp, device_id, punch_code, batch_id=None, force_create=False):
    """Create a Machine Log row from a device payload."""
    try:
        log_id = _generate_machine_log_id(enroll_no, timestamp, device_id, punch_code)

        if not force_create:
            existing_log = frappe.db.exists("Machine Log", {"id": log_id})
            if existing_log:
                return 200, {
                    "status": "success",
                    "message": "Log already exists",
                    "data": {"name": existing_log, "id": log_id},
                    "duplicate": True,
                }

        parsed_time = get_datetime(timestamp)

        machine_log = frappe.new_doc("Machine Log")
        machine_log.id = log_id
        machine_log.enroll_no = str(enroll_no)
        machine_log.time = parsed_time
        machine_log.date = getdate(parsed_time)
        machine_log.device = device_id
        machine_log.punch = str(punch_code)
        machine_log.employee_check_in_created = 0

        employee = _resolve_employee_from_enroll_no(enroll_no)
        if employee:
            machine_log.employee = employee["name"]
            machine_log.type = _determine_punch_type(punch_code, device_id)

        if batch_id and hasattr(machine_log, "batch_id"):
            machine_log.batch_id = batch_id

        machine_log.flags.ignore_permissions = True
        machine_log.insert()

        return 200, {
            "status": "success",
            "message": "Machine log created successfully",
            "data": {
                "name": machine_log.name,
                "id": machine_log.id,
                "employee_resolved": bool(employee),
            },
        }

    except Exception as e:
        frappe.log_error(f"Error creating machine log: {str(e)}")
        return 500, {"status": "error", "message": str(e), "data": None}


def create_bulk_machine_logs(logs_data):
    """Create multiple Machine Log rows from one device batch."""
    try:
        logs = json.loads(logs_data) if isinstance(logs_data, str) else logs_data
        batch_id = frappe.generate_hash(length=12)

        results = {
            "batch_id": batch_id,
            "total_records": len(logs),
            "successful": 0,
            "duplicates": 0,
            "failed": 0,
            "results": [],
        }

        batch_size = 100
        for i in range(0, len(logs), batch_size):
            batch_logs = logs[i : i + batch_size]

            for log_data in batch_logs:
                status_code, result = create_machine_log(
                    enroll_no=log_data.get("enroll_no"),
                    timestamp=log_data.get("timestamp"),
                    device_id=log_data.get("device_id"),
                    punch_code=log_data.get("punch_code"),
                    batch_id=batch_id,
                    force_create=False,
                )

                results["results"].append(result)
                if status_code == 200 and result["status"] == "success":
                    if result.get("duplicate"):
                        results["duplicates"] += 1
                    else:
                        results["successful"] += 1
                else:
                    results["failed"] += 1

            frappe.db.commit()

        return results

    except Exception as e:
        frappe.log_error(f"Error in bulk machine log creation: {str(e)}")
        return {"status": "error", "message": f"Bulk operation failed: {str(e)}"}


def update_lastsynced_record_log_timestamp(device_id, last_synced_record_datetime):
    try:
        frappe.db.sql(
            """
            UPDATE `tabFingerprint Machine`
            SET last_synced_record_datetime = %s
            WHERE device_id = %s
            """,
            (last_synced_record_datetime, device_id),
        )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            title="Error Updating Last Synced Record Timestamp",
            message=f"Device ID: {device_id}, Error: {str(e)}",
        )
        return 500, {"status": "error", "message": str(e)}


def _generate_machine_log_id(enroll_no, timestamp, device_id, punch_code):
    data_string = f"{enroll_no}_{timestamp}_{device_id}_{punch_code}"
    return hashlib.md5(data_string.encode()).hexdigest()[:16].upper()


def _resolve_employee_from_enroll_no(enroll_no):
    try:
        return frappe.db.get_value(
            "Employee",
            {"attendance_device_id": enroll_no, "status": "Active"},
            ["name", "employee_name"],
            as_dict=True,
        )
    except Exception:
        return None


def _determine_punch_type(punch_code, device_id=None):
    device_config = _get_device_config(device_id)
    punch_code = int(punch_code) if str(punch_code).isdigit() else punch_code

    if device_config:
        if punch_code in device_config.get("in_punch_codes", [0, 4]):
            return "IN"
        if punch_code in device_config.get("out_punch_codes", [1, 5]):
            return "OUT"

    if punch_code in [0, 4]:
        return "IN"
    if punch_code in [1, 5]:
        return "OUT"

    return None


def _get_device_config(device_id):
    if not device_id:
        return None

    try:
        device_doc = frappe.get_doc("Fingerprint Machine", device_id)
        return {
            "in_punch_codes": getattr(device_doc, "in_punch_codes", [0, 4]),
            "out_punch_codes": getattr(device_doc, "out_punch_codes", [1, 5]),
        }
    except Exception:
        return None
