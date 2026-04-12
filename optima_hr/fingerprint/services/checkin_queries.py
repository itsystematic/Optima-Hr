from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe.utils import get_datetime

MachineLogRow = dict[str, Any]
EmployeeRow = dict[str, Any]
CheckinKey = tuple[str, datetime, str | None]
CheckinRow = dict[str, Any]


def get_pending_machine_logs(limit_count: int) -> list[MachineLogRow]:
    """Return pending logs newest-first so fresh logs are not blocked by stale backlog."""
    return frappe.db.sql(
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


def get_active_employee_map(machine_logs: list[MachineLogRow]) -> dict[str, EmployeeRow]:
    """Return active employees for the batch so we avoid one lookup per log."""
    employee_names = sorted({log["employee"] for log in machine_logs if log.get("employee")})
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


def get_existing_checkin_map(machine_logs: list[MachineLogRow]) -> dict[CheckinKey, CheckinRow]:
    """Return existing checkins keyed by business identity so duplicate checks stay in memory."""
    employee_names = sorted({log["employee"] for log in machine_logs if log.get("employee")})
    if not employee_names:
        return {}

    timestamps = [get_datetime(log["timestamp"]) for log in machine_logs if log.get("timestamp")]
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
        make_checkin_key(checkin.employee, checkin.time, checkin.log_type): checkin
        for checkin in checkins
    }


def make_checkin_key(employee: str, timestamp: Any, log_type: str | None) -> CheckinKey:
    """Build a stable duplicate key so machine logs and checkins compare the same way."""
    return (employee, get_datetime(timestamp).replace(microsecond=0), log_type)
