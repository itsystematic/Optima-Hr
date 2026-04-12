import frappe

from optima_hr.fingerprint.services.checkin_sync import sync_employee_checkins
from optima_hr.fingerprint.services.machine_log import (
    create_bulk_machine_logs as create_bulk_machine_logs_service,
    create_machine_log as create_machine_log_service,
    update_lastsynced_record_log_timestamp,
)


@frappe.whitelist()
def create_machine_log(
    enroll_no: str,
    timestamp: str,
    device_id: str,
    punch_code: str,
    batch_id: str | None = None,
    force_create: bool = False,
) -> tuple[int, dict]:
    """Create one machine log through the API so transport stays separate from business rules."""
    # Keep the API thin so business rules stay testable outside the transport layer.
    return create_machine_log_service(
        enroll_no=enroll_no,
        timestamp=timestamp,
        device_id=device_id,
        punch_code=punch_code,
        batch_id=batch_id,
        force_create=force_create,
    )


@frappe.whitelist(allow_guest=True)
def create_bulk_machine_logs(logs_data: str | list[dict]) -> dict:
    """Create a batch of machine logs through the API so device uploads use one entrypoint."""
    return create_bulk_machine_logs_service(logs_data)


@frappe.whitelist()
def create_employee_checkin() -> str:
    """Sync pending machine logs so scheduler and UI share the same behavior."""
    # Scheduler and UI both enter through one route to avoid drift in sync behavior.
    return sync_employee_checkins()


@frappe.whitelist()
def update_lastsynced_recodrd_log_timestamp(
    device_id: str, last_synced_record_datetime: str
) -> tuple[int, dict] | None:
    """Update the raw device cursor so pull-based clients can resume from the last imported log."""
    return update_lastsynced_record_log_timestamp(device_id, last_synced_record_datetime)
