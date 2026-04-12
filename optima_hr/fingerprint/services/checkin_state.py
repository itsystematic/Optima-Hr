from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import add_to_date, get_datetime


def mark_machine_logs_processed(processed_log_names: list[str]) -> None:
    """Mark source logs in one write so sync progress is durable and cheap."""
    if not processed_log_names:
        return

    frappe.db.sql(
        """
        UPDATE `tabMachine Log`
        SET employee_check_in_created = 1
        WHERE name IN ({})
        """.format(",".join(["%s"] * len(processed_log_names))),
        processed_log_names,
    )
    frappe.db.commit()


def track_shift_last_sync(
    shift_sync_updates: dict[str, Any], shift_name: str | None, shift_actual_end: Any
) -> None:
    """Track the farthest shift cursor so attendance resumes from the correct cutoff."""
    if not shift_name or not shift_actual_end:
        return

    new_sync_time = add_to_date(get_datetime(shift_actual_end), minutes=1, as_datetime=True)
    current_sync_time = shift_sync_updates.get(shift_name)

    if not current_sync_time or new_sync_time > current_sync_time:
        shift_sync_updates[shift_name] = new_sync_time


def track_device_last_sync(
    device_sync_updates: dict[str, Any], device_id: str | None, timestamp: Any
) -> None:
    """Track each device separately so one branch machine does not overwrite another."""
    if not device_id or not timestamp:
        return

    sync_time = get_datetime(timestamp)
    current_sync_time = device_sync_updates.get(device_id)

    if not current_sync_time or sync_time > current_sync_time:
        device_sync_updates[device_id] = sync_time


def update_shift_last_syncs(shift_sync_updates: dict[str, Any]) -> None:
    """Persist shift cursors after one bulk read so repeated get_value calls are avoided."""
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


def update_fingerprint_machine_last_syncs(device_sync_updates: dict[str, Any]) -> None:
    """Persist device cursors after one bulk read so per-device checks stay lightweight."""
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


def build_sync_summary(
    total_logs: int,
    created_count: int,
    duplicate_count: int,
    skipped_no_shift_count: int,
    skipped_inactive_count: int,
    failed_count: int,
) -> str:
    """Return a compact operator summary so the button result explains what happened."""
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
