import frappe

from optima_hr.fingerprint.services.checkin_sync import sync_employee_checkins
from optima_hr.fingerprint.services.machine_log import (
    create_bulk_machine_logs as create_bulk_machine_logs_service,
    create_machine_log as create_machine_log_service,
    update_lastsynced_record_log_timestamp,
)


@frappe.whitelist()
def create_machine_log(enroll_no, timestamp, device_id, punch_code, batch_id=None, force_create=False):
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
def create_bulk_machine_logs(logs_data):
    return create_bulk_machine_logs_service(logs_data)


@frappe.whitelist()
def create_employee_checkin():
    # Scheduler and UI both enter through one route to avoid drift in sync behavior.
    return sync_employee_checkins()


@frappe.whitelist()
def update_lastsynced_recodrd_log_timestamp(device_id, last_synced_record_datetime):
    return update_lastsynced_record_log_timestamp(device_id, last_synced_record_datetime)
