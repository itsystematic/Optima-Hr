import frappe
from frappe.utils import add_to_date, get_datetime

from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift


def sync_employee_checkins():
    """Convert pending Machine Logs into Employee Checkins."""
    limit_count = 200
    machine_logs = frappe.db.sql(
        """
        SELECT name, employee, time AS timestamp, type AS log_type, device
        FROM `tabMachine Log`
        WHERE employee IS NOT NULL AND employee_check_in_created = 0
        ORDER BY time DESC
        LIMIT %(limit)s
        """,
        {"limit": limit_count},
        as_dict=True,
    )

    if not machine_logs:
        return "No pending machine logs were found."

    active_employees = _get_active_employee_map(machine_logs)
    existing_checkins = _get_existing_checkin_map(machine_logs)

    failed_logs = []
    processed_log_names = []
    shift_sync_updates = {}
    device_sync_updates = {}
    skipped_no_shift_logs = []
    skipped_inactive_logs = []
    created_count = 0
    duplicate_count = 0

    for log in machine_logs:
        try:
            employee = active_employees.get(log.employee)
            if not employee:
                skipped_inactive_logs.append(f"[{log.name}] {log.employee} @ {log.timestamp}")
                continue

            existing_checkin = existing_checkins.get(_make_checkin_key(log.employee, log.timestamp, log.log_type))
            if existing_checkin:
                processed_log_names.append(log.name)
                duplicate_count += 1
                # Duplicate checkins should still retire their source machine log.
                _track_device_last_sync(device_sync_updates, log.device, log.timestamp)
                _track_shift_last_sync(
                    shift_sync_updates,
                    existing_checkin.shift,
                    existing_checkin.shift_actual_end,
                )
                continue

            # Missing historic shifts should not block newer valid logs in the same queue.
            if not get_actual_start_end_datetime_of_shift(employee.name, get_datetime(log.timestamp), True):
                skipped_no_shift_logs.append(f"[{log.name}] {employee.employee_name} @ {log.timestamp}")
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
            checkin.insert()

            # Machine logs are the source of truth for retry state, not Employee Checkin rows.
            processed_log_names.append(log.name)
            created_count += 1
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

    if skipped_no_shift_logs:
        frappe.logger().info(
            "[FINGERPRINT] Skipped logs without shift assignment:\n" + "\n".join(skipped_no_shift_logs)
        )

    if skipped_inactive_logs:
        frappe.logger().info(
            "[FINGERPRINT] Skipped logs for inactive or missing employees:\n"
            + "\n".join(skipped_inactive_logs)
        )

    return _build_sync_summary(
        total_logs=len(machine_logs),
        created_count=created_count,
        duplicate_count=duplicate_count,
        skipped_no_shift_count=len(skipped_no_shift_logs),
        skipped_inactive_count=len(skipped_inactive_logs),
        failed_count=len(failed_logs),
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
    new_sync_time = add_to_date(get_datetime(shift_actual_end), minutes=1, as_datetime=True)
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
    if not shift_sync_updates:
        return

    current_syncs = {
        row.name: row.last_sync_of_checkin
        for row in frappe.get_all(
            "Shift Type",
            filters={"name": ["in", list(shift_sync_updates)]},
            fields=["name", "last_sync_of_checkin"],
        )
    }

    for shift_name, max_timestamp in shift_sync_updates.items():
        try:
            current_last_sync = current_syncs.get(shift_name)
            if not current_last_sync or get_datetime(max_timestamp) > get_datetime(current_last_sync):
                frappe.db.set_value("Shift Type", shift_name, "last_sync_of_checkin", max_timestamp)
                frappe.logger().info(
                    f"[FINGERPRINT] Updated last sync for shift {shift_name} to {max_timestamp}"
                )
        except Exception as e:
            frappe.log_error(f"Error updating shift sync for {shift_name}: {str(e)}")


def _update_fingerprint_machine_last_syncs(device_sync_updates):
    if not device_sync_updates:
        return

    current_syncs = {
        row.name: row.last_sync
        for row in frappe.get_all(
            "Fingerprint Machine",
            filters={"name": ["in", list(device_sync_updates)]},
            fields=["name", "last_sync"],
        )
    }

    for device_id, max_timestamp in device_sync_updates.items():
        try:
            current_last_sync = current_syncs.get(device_id)
            if not current_last_sync or get_datetime(max_timestamp) > get_datetime(current_last_sync):
                frappe.db.set_value("Fingerprint Machine", device_id, "last_sync", max_timestamp)
        except Exception as e:
            frappe.log_error(f"Error updating machine sync for {device_id}: {str(e)}")


def _get_active_employee_map(machine_logs):
    employee_names = sorted({log.employee for log in machine_logs if log.employee})
    if not employee_names:
        return {}

    return {
        row.name: row
        for row in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_names], "status": "Active"},
            fields=["name", "employee_name"],
        )
    }


def _get_existing_checkin_map(machine_logs):
    employee_names = sorted({log.employee for log in machine_logs if log.employee})
    if not employee_names:
        return {}

    timestamps = [get_datetime(log.timestamp) for log in machine_logs if log.timestamp]
    if not timestamps:
        return {}

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_names],
            "time": ["between", [min(timestamps), max(timestamps)]],
        },
        fields=["name", "employee", "time", "log_type", "shift", "shift_actual_end"],
    )

    return {
        _make_checkin_key(checkin.employee, checkin.time, checkin.log_type): checkin
        for checkin in checkins
    }


def _make_checkin_key(employee, timestamp, log_type):
    return (employee, get_datetime(timestamp).replace(microsecond=0), log_type)


def _build_sync_summary(
    total_logs,
    created_count,
    duplicate_count,
    skipped_no_shift_count,
    skipped_inactive_count,
    failed_count,
):
    parts = [f"Processed {total_logs} logs."]

    if created_count:
        parts.append(f"Created {created_count} check-ins.")
    if duplicate_count:
        parts.append(f"Marked {duplicate_count} duplicate logs as processed.")
    if skipped_no_shift_count:
        parts.append(f"Skipped {skipped_no_shift_count} logs with no shift assignment.")
    if skipped_inactive_count:
        parts.append(f"Skipped {skipped_inactive_count} logs for inactive employees.")
    if failed_count:
        parts.append(f"{failed_count} logs still failed. Check Error Log for details.")

    return "\n".join(parts)
