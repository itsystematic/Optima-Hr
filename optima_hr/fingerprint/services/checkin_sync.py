from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import frappe
from frappe.utils import get_datetime

from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from optima_hr.fingerprint.services.checkin_queries import (
    CheckinRow,
    EmployeeRow,
    MachineLogRow,
    get_active_employee_map,
    get_existing_checkin_map,
    get_pending_machine_logs,
    make_checkin_key,
)
from optima_hr.fingerprint.services.checkin_state import (
    build_sync_summary,
    mark_machine_logs_processed,
    track_device_last_sync,
    track_shift_last_sync,
    update_fingerprint_machine_last_syncs,
    update_shift_last_syncs,
)


@dataclass
class SyncStats:
    """Collect sync outcomes so the orchestrator stays focused on workflow."""

    failed_logs: list[str] = field(default_factory=list)
    processed_log_names: list[str] = field(default_factory=list)
    shift_sync_updates: dict[str, Any] = field(default_factory=dict)
    device_sync_updates: dict[str, Any] = field(default_factory=dict)
    skipped_no_shift_logs: list[str] = field(default_factory=list)
    skipped_inactive_logs: list[str] = field(default_factory=list)
    created_count: int = 0
    duplicate_count: int = 0


def sync_employee_checkins(limit_count: int = 200) -> str:
    """Create Employee Checkins from pending logs so recent valid punches sync first."""
    machine_logs = get_pending_machine_logs(limit_count)
    if not machine_logs:
        return "No pending machine logs were found."

    active_employees = get_active_employee_map(machine_logs)
    existing_checkins = get_existing_checkin_map(machine_logs)
    stats = SyncStats()

    for log in machine_logs:
        _process_machine_log(log, active_employees, existing_checkins, stats)

    mark_machine_logs_processed(stats.processed_log_names)
    update_shift_last_syncs(stats.shift_sync_updates)
    update_fingerprint_machine_last_syncs(stats.device_sync_updates)
    _log_sync_outcomes(stats)

    return build_sync_summary(
        total_logs=len(machine_logs),
        created_count=stats.created_count,
        duplicate_count=stats.duplicate_count,
        skipped_no_shift_count=len(stats.skipped_no_shift_logs),
        skipped_inactive_count=len(stats.skipped_inactive_logs),
        failed_count=len(stats.failed_logs),
    )


def _process_machine_log(
    log: MachineLogRow,
    active_employees: dict[str, EmployeeRow],
    existing_checkins: dict[tuple[str, Any, str | None], CheckinRow],
    stats: SyncStats,
) -> None:
    """Process one log so branching rules stay isolated from the batch orchestration."""
    try:
        employee = active_employees.get(log["employee"])
        if not employee:
            stats.skipped_inactive_logs.append(f"[{log['name']}] {log['employee']} @ {log['timestamp']}")
            return

        existing_checkin = existing_checkins.get(
            make_checkin_key(log["employee"], log["timestamp"], log.get("log_type"))
        )
        if existing_checkin:
            _handle_existing_checkin(log, existing_checkin, stats)
            return

        if not _has_shift_assignment(employee["name"], log["timestamp"]):
            stats.skipped_no_shift_logs.append(
                f"[{log['name']}] {employee['employee_name']} @ {log['timestamp']}"
            )
            return

        _create_employee_checkin(log, employee, stats)
    except Exception as e:
        stats.failed_logs.append(f"[{log['name']}] {str(e)}")


def _handle_existing_checkin(log: MachineLogRow, existing_checkin: CheckinRow, stats: SyncStats) -> None:
    """Retire duplicate source logs so the queue does not retry work that already exists."""
    stats.processed_log_names.append(log["name"])
    stats.duplicate_count += 1
    track_device_last_sync(stats.device_sync_updates, log.get("device"), log.get("timestamp"))
    track_shift_last_sync(
        stats.shift_sync_updates,
        existing_checkin.get("shift"),
        existing_checkin.get("shift_actual_end"),
    )


def _has_shift_assignment(employee_name: str, timestamp: Any) -> bool:
    """Check shift existence quietly so old no-shift logs do not spam the operator UI."""
    return bool(get_actual_start_end_datetime_of_shift(employee_name, get_datetime(timestamp), True))


def _create_employee_checkin(log: MachineLogRow, employee: EmployeeRow, stats: SyncStats) -> None:
    """Insert a checkin from one machine log so retry state and sync cursors stay aligned."""
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee["name"]
    checkin.employee_name = employee["employee_name"]
    checkin.time = log["timestamp"]
    checkin.device_id = log.get("device")
    checkin.log_type = log.get("log_type")
    checkin.latitude = None
    checkin.longitude = None
    checkin.skip_auto_attendance = 0
    checkin.insert()

    stats.processed_log_names.append(log["name"])
    stats.created_count += 1
    track_device_last_sync(stats.device_sync_updates, log.get("device"), log.get("timestamp"))
    track_shift_last_sync(stats.shift_sync_updates, checkin.shift, checkin.shift_actual_end)


def _log_sync_outcomes(stats: SyncStats) -> None:
    """Log skipped and failed rows so operators can inspect edge cases without UI noise."""
    if stats.failed_logs:
        frappe.log_error(
            title="Employee Checkin Creation Errors",
            message="Failed Logs:\n" + "\n".join(stats.failed_logs),
        )

    if stats.skipped_no_shift_logs:
        frappe.logger().info(
            "[FINGERPRINT] Skipped logs without shift assignment:\n" + "\n".join(stats.skipped_no_shift_logs)
        )

    if stats.skipped_inactive_logs:
        frappe.logger().info(
            "[FINGERPRINT] Skipped logs for inactive or missing employees:\n"
            + "\n".join(stats.skipped_inactive_logs)
        )
