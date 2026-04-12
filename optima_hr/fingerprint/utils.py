"""Backwards-compatible routes while callers move from fingerprint.utils to fingerprint.api."""

from optima_hr.fingerprint.api import (
    create_bulk_machine_logs,
    create_employee_checkin,
    create_machine_log,
    update_lastsynced_recodrd_log_timestamp,
)
