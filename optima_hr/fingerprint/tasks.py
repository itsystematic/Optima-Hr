import frappe
from frappe.utils import nowdate, add_days

def dail():
    """Daily task to delete old device logs."""
    delete_old_devices_logs()


def delete_old_devices_logs():
    """Delete old logs from Fingerprint Machine based on the number of days configured."""
    # Get the number of days from Zkteco Settings
    devices = frappe.get_all("Fingerprint Machine")
    for device in devices:
        no_of_days = frappe.get_cached_value("Fingerprint Machine", device.name, "no_of_days")

        if not no_of_days:
            no_of_days = 60
        # Delete logs where employee_check_in_created = 1 and time before no_of_days
        frappe.db.sql("""
            DELETE FROM `tabMachine Log`
            WHERE employee_check_in_created = 1
            AND time < %s
        """, (add_days(nowdate(), -no_of_days),))
        frappe.db.commit()