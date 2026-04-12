from datetime import timedelta

import frappe
from frappe.utils import get_datetime


def sync_employee_checkins():
    """Convert pending Machine Logs into Employee Checkins."""
    limit_count = 200
    machine_logs = frappe.db.sql(
        """
        SELECT name, employee, time AS timestamp, type AS log_type, device
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
                {"employee": log.employee, "time": log.timestamp, "log_type": log.log_type},
            )
            if existing_checkin:
                processed_log_names.append(log.name)
                # Duplicate checkins should still retire their source machine log.
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

            checkin = frappe.new_doc("Employee Checkin")
            checkin.employee = employee.name
            checkin.employee_name = employee.employee_name
            checkin.time = log.timestamp
            checkin.device_id = log.device
            checkin.log_type = log.log_type
            checkin.latitude = None
            checkin.longitude = None
            checkin.skip_auto_attendance = 0

            checkin.fetch_shift()
            checkin.insert()

            # Machine logs are the source of truth for retry state, not Employee Checkin rows.
            processed_log_names.append(log.name)
            _track_device_last_sync(device_sync_updates, log.device, log.timestamp)
            _track_shift_last_sync(shift_sync_updates, checkin.shift, checkin.shift_actual_end)

        except Exception as e:
            failed_logs.append(f"[{log.name}] {str(e)}")

    _mark_machine_logs_processed(processed_log_names)
    _update_shift_last_syncs(shift_sync_updates)
    _update_fingerprint_machine_last_syncs(device_sync_updates)

    if failed_logs:
        frappe.log_error(
            title="Employee Checkin Creation Errors",
            message="Failed Logs:\n" + "\n".join(failed_logs),
        )


def _mark_machine_logs_processed(processed_log_names):
    if not processed_log_names:
        return

    # Batch update keeps one sync run from doing hundreds of small writes.
    frappe.db.sql(
        """
        UPDATE `tabMachine Log`
        SET employee_check_in_created = 1
        WHERE name IN ({})
        """.format(",".join(["%s"] * len(processed_log_names))),
        processed_log_names,
    )
    frappe.db.commit()


def _track_shift_last_sync(shift_sync_updates, shift_name, shift_actual_end):
    if not shift_name or not shift_actual_end:
        return

    # HRMS processes attendance up to last_sync_of_checkin, so we advance past shift end.
    new_sync_time = get_datetime(shift_actual_end) + timedelta(minutes=1)
    current_sync_time = shift_sync_updates.get(shift_name)

    if not current_sync_time or new_sync_time > current_sync_time:
        shift_sync_updates[shift_name] = new_sync_time


def _track_device_last_sync(device_sync_updates, device_id, timestamp):
    if not device_id or not timestamp:
        return

    # Each machine keeps its own sync cursor so branch devices do not overwrite each other.
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
