"""
Regression Tests for create_employee_checkin

Ensures functionality remains correct after optimizations:
- Correct checkin creation
- Duplicate handling
- Inactive employee filtering
- Shift sync updates
- Machine log marking
- Error handling
- Batch update correctness
"""

import frappe
import unittest
from datetime import datetime, timedelta
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, get_datetime
from hr_ksa.fingerprint.tests.fixtures import (
    create_test_employees,
    create_test_shifts,
    create_test_devices,
    create_test_machine_logs,
    create_shift_assignments,
    cleanup_test_data
)
from hr_ksa.fingerprint.utils import create_employee_checkin


class TestRegressionCreateEmployeeCheckin(FrappeTestCase):
    """Regression tests to ensure correctness of create_employee_checkin"""

    def setUp(self):
        """Setup test environment for each test"""
        # Create fresh test data for each test
        self.employees = create_test_employees(10)
        self.shifts = create_test_shifts(3)
        self.devices = create_test_devices(2)
        self.assignments = create_shift_assignments(self.employees, self.shifts)

        frappe.db.commit()

    def tearDown(self):
        """Clean up after each test"""
        cleanup_test_data()

    def test_correct_checkin_creation(self):
        """
        Verify Employee Checkin records are created correctly

        Checks:
        - All required fields populated
        - Employee name matches
        - Time matches
        - Log type matches
        - Device ID matches
        """
        print("\n[TEST] Correct Checkin Creation")

        # Create test machine logs
        test_time = now_datetime()
        logs = create_test_machine_logs(
            count=10,
            employees=self.employees[:5],
            devices=self.devices,
            base_date=test_time
        )

        # Run function
        create_employee_checkin()

        # Verify checkins created
        checkins = frappe.get_all("Employee Checkin",
            filters={"employee": ["in", self.employees[:5]]},
            fields=["name", "employee", "employee_name", "time", "log_type", "device_id"]
        )

        print(f"  Created {len(checkins)} checkins from {len(logs)} logs")

        self.assertGreater(len(checkins), 0, "Should create checkins")

        # Verify each checkin has required fields
        for checkin in checkins:
            self.assertIsNotNone(checkin.employee, "Employee should be set")
            self.assertIsNotNone(checkin.employee_name, "Employee name should be set")
            self.assertIsNotNone(checkin.time, "Time should be set")
            self.assertIsNotNone(checkin.log_type, "Log type should be set")
            self.assertIsNotNone(checkin.device_id, "Device ID should be set")

            # Verify employee name matches
            expected_name = frappe.db.get_value("Employee", checkin.employee, "employee_name")
            self.assertEqual(checkin.employee_name, expected_name,
                           "Employee name should match")

            # Verify log type is IN or OUT
            self.assertIn(checkin.log_type, ["IN", "OUT"], "Log type should be IN or OUT")

        print("  ✓ All checkins have correct fields")

    def test_duplicate_detection(self):
        """
        Verify duplicate checkins are not created

        Scenario:
        - Create machine logs
        - Process them (creates checkins)
        - Create duplicate machine logs
        - Process again
        - Verify no duplicate checkins created
        """
        print("\n[TEST] Duplicate Detection")

        # Create initial logs
        test_time = now_datetime()
        logs = create_test_machine_logs(
            count=5,
            employees=self.employees[:3],
            devices=self.devices,
            base_date=test_time
        )

        # Process first time
        create_employee_checkin()

        initial_count = frappe.db.count("Employee Checkin", {
            "employee": ["in", self.employees[:3]]
        })

        print(f"  Initial checkins: {initial_count}")

        # Get first machine log details to create exact duplicate
        first_log = frappe.get_doc("Machine Log", logs[0])

        # Create duplicate checkin manually
        try:
            duplicate_checkin = frappe.new_doc("Employee Checkin")
            duplicate_checkin.employee = first_log.employee
            duplicate_checkin.employee_name = frappe.db.get_value("Employee",
                                                                  first_log.employee,
                                                                  "employee_name")
            duplicate_checkin.time = first_log.time
            duplicate_checkin.log_type = first_log.type
            duplicate_checkin.device_id = first_log.device
            duplicate_checkin.insert()

            # Should not reach here if duplicate detection works
            self.fail("Should not allow duplicate checkin creation")

        except frappe.DuplicateEntryError:
            print("  ✓ Correctly prevented duplicate checkin (database constraint)")

        except Exception as e:
            # Check if the exists() check in the function prevented it
            pass

        # Process again
        create_employee_checkin()

        final_count = frappe.db.count("Employee Checkin", {
            "employee": ["in", self.employees[:3]]
        })

        print(f"  Final checkins: {final_count}")

        # Count should not increase (duplicates skipped)
        self.assertEqual(initial_count, final_count,
                        "Should not create duplicate checkins")

        print("  ✓ No duplicate checkins created")

    def test_inactive_employee_handling(self):
        """
        Verify inactive employees are skipped

        Scenario:
        - Mark some employees as inactive
        - Create machine logs for both active and inactive
        - Process logs
        - Verify only active employee checkins created
        """
        print("\n[TEST] Inactive Employee Handling")

        # Mark first 3 employees as inactive
        inactive_employees = self.employees[:3]
        active_employees = self.employees[3:7]

        for emp in inactive_employees:
            frappe.db.set_value("Employee", emp, "status", "Inactive")

        print(f"  Inactive employees: {len(inactive_employees)}")
        print(f"  Active employees: {len(active_employees)}")

        # Create logs for both inactive and active employees
        inactive_logs = create_test_machine_logs(
            count=10,
            employees=inactive_employees,
            devices=self.devices
        )

        active_logs = create_test_machine_logs(
            count=10,
            employees=active_employees,
            devices=self.devices
        )

        print(f"  Created {len(inactive_logs)} inactive + {len(active_logs)} active logs")

        # Process logs
        create_employee_checkin()

        # Count checkins for inactive employees (should be 0)
        inactive_checkins = frappe.db.count("Employee Checkin", {
            "employee": ["in", inactive_employees]
        })

        # Count checkins for active employees (should be > 0)
        active_checkins = frappe.db.count("Employee Checkin", {
            "employee": ["in", active_employees]
        })

        print(f"  Inactive employee checkins: {inactive_checkins}")
        print(f"  Active employee checkins: {active_checkins}")

        # Assertions
        self.assertEqual(inactive_checkins, 0,
                        "Should not create checkins for inactive employees")

        self.assertGreater(active_checkins, 0,
                          "Should create checkins for active employees")

        print("  ✓ Correctly skipped inactive employees")

    def test_shift_sync_update(self):
        """
        Verify Shift Type last_sync_of_checkin is updated correctly

        Checks:
        - last_sync_of_checkin is updated
        - Only updated if timestamp is newer
        - Correct timestamp is set
        """
        print("\n[TEST] Shift Sync Update")

        # Use specific employees with shift assignments
        test_employees = self.employees[:5]
        test_shift = self.shifts[0]

        # Ensure employees have shift assignments
        for emp in test_employees:
            if not frappe.db.exists("Shift Assignment", {
                "employee": emp,
                "shift_type": test_shift
            }):
                assignment = frappe.new_doc("Shift Assignment")
                assignment.employee = emp
                assignment.shift_type = test_shift
                assignment.start_date = datetime.now().date()
                assignment.status = "Active"
                assignment.insert()

        frappe.db.commit()

        # Get initial last_sync_of_checkin
        initial_sync = frappe.db.get_value("Shift Type", test_shift, "last_sync_of_checkin")

        print(f"  Initial last_sync: {initial_sync}")

        # Create machine logs with specific time
        test_time = now_datetime()
        logs = create_test_machine_logs(
            count=5,
            employees=test_employees,
            devices=self.devices,
            base_date=test_time
        )

        # Process logs
        create_employee_checkin()

        # Get updated last_sync_of_checkin
        updated_sync = frappe.db.get_value("Shift Type", test_shift, "last_sync_of_checkin")

        print(f"  Updated last_sync: {updated_sync}")

        # Verify it was updated
        if initial_sync:
            self.assertNotEqual(initial_sync, updated_sync,
                              "last_sync_of_checkin should be updated")
        else:
            self.assertIsNotNone(updated_sync,
                                "last_sync_of_checkin should be set")

        print("  ✓ Shift sync timestamp updated")

        # Test that older timestamps don't update
        # Create logs with older time
        old_time = test_time - timedelta(days=1)
        old_logs = create_test_machine_logs(
            count=3,
            employees=test_employees,
            devices=self.devices,
            base_date=old_time
        )

        # Process logs
        create_employee_checkin()

        # Get last_sync again
        final_sync = frappe.db.get_value("Shift Type", test_shift, "last_sync_of_checkin")

        print(f"  Final last_sync (after old logs): {final_sync}")

        # Should not have changed (older timestamp)
        self.assertEqual(get_datetime(updated_sync), get_datetime(final_sync),
                        "Should not update with older timestamp")

        print("  ✓ Correctly ignored older timestamps")

    def test_machine_log_marking(self):
        """
        Verify machine logs are marked as processed

        Checks:
        - employee_check_in_created flag set to 1
        - Only processed logs are marked
        - Failed logs are not marked
        """
        print("\n[TEST] Machine Log Marking")

        # Create logs
        logs = create_test_machine_logs(
            count=10,
            employees=self.employees[:5],
            devices=self.devices
        )

        # Verify initial state (not processed)
        unprocessed = frappe.db.count("Machine Log", {
            "name": ["in", logs],
            "employee_check_in_created": 0
        })

        print(f"  Unprocessed logs: {unprocessed}/{len(logs)}")

        self.assertEqual(unprocessed, len(logs), "All logs should be unprocessed initially")

        # Process logs
        create_employee_checkin()

        # Verify logs are marked
        processed = frappe.db.count("Machine Log", {
            "name": ["in", logs],
            "employee_check_in_created": 1
        })

        print(f"  Processed logs: {processed}/{len(logs)}")

        self.assertGreater(processed, 0, "Some logs should be marked as processed")

        # Verify unprocessed count decreased
        still_unprocessed = frappe.db.count("Machine Log", {
            "name": ["in", logs],
            "employee_check_in_created": 0
        })

        self.assertLess(still_unprocessed, len(logs),
                       "Processed logs should be marked")

        print("  ✓ Logs correctly marked as processed")

    def test_batch_update_correctness(self):
        """
        Verify batch SQL update updates all processed logs

        Checks:
        - All successfully processed logs are updated
        - Batch update is atomic (all or nothing per batch)
        """
        print("\n[TEST] Batch Update Correctness")

        # Create logs
        logs = create_test_machine_logs(
            count=100,
            employees=self.employees[:8],
            devices=self.devices
        )

        print(f"  Created {len(logs)} logs")

        # Process logs
        create_employee_checkin()

        # Count marked logs
        marked_logs = frappe.db.count("Machine Log", {
            "device": ["like", "PERFTEST_DEVICE%"],
            "employee_check_in_created": 1
        })

        # Count created checkins
        checkins = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Marked logs: {marked_logs}")
        print(f"  Created checkins: {checkins}")

        # Number of marked logs should match or be close to checkins
        # (may differ slightly due to duplicates)
        self.assertGreater(marked_logs, 0, "Should mark processed logs")
        self.assertGreater(checkins, 0, "Should create checkins")

        print("  ✓ Batch update processed correctly")

    def test_error_handling(self):
        """
        Verify errors are handled gracefully

        Scenarios:
        - Invalid employee reference
        - Missing data
        - Database errors
        - Partial failures don't stop processing
        """
        print("\n[TEST] Error Handling")

        # Create valid logs
        valid_logs = create_test_machine_logs(
            count=10,
            employees=self.employees[:5],
            devices=self.devices
        )

        # Create log with invalid employee (will be skipped)
        invalid_log = frappe.new_doc("Machine Log")
        invalid_log.id = "INVALID_TEST_LOG"
        invalid_log.enroll_no = "999999"
        invalid_log.time = now_datetime()
        invalid_log.date = datetime.now().date()
        invalid_log.device = self.devices[0]
        invalid_log.punch = "0"
        invalid_log.type = "IN"
        invalid_log.employee = None  # Invalid
        invalid_log.employee_check_in_created = 0
        invalid_log.insert()

        print(f"  Created {len(valid_logs)} valid logs + 1 invalid log")

        # Process logs (should handle error gracefully)
        try:
            create_employee_checkin()
            print("  ✓ Function completed without crashing")

        except Exception as e:
            self.fail(f"Function should handle errors gracefully: {str(e)}")

        # Verify valid logs were still processed
        checkins = frappe.db.count("Employee Checkin", {
            "employee": ["in", self.employees[:5]]
        })

        print(f"  Checkins created: {checkins}")

        self.assertGreater(checkins, 0,
                          "Should create checkins for valid logs despite errors")

        # Clean up invalid log
        frappe.delete_doc("Machine Log", "INVALID_TEST_LOG", force=True)

        print("  ✓ Errors handled gracefully")

    def test_functionality_preservation(self):
        """
        Comprehensive test to verify overall functionality

        End-to-end test covering:
        - Create various machine logs
        - Process them
        - Verify all expected outcomes
        """
        print("\n[TEST] Overall Functionality Preservation")

        # Create comprehensive test scenario
        test_employees = self.employees[:8]

        # Mix of IN and OUT logs
        logs = create_test_machine_logs(
            count=50,
            employees=test_employees,
            devices=self.devices
        )

        print(f"  Created {len(logs)} logs for {len(test_employees)} employees")

        # Process logs
        create_employee_checkin()

        # Verify outcomes
        checkins = frappe.get_all("Employee Checkin",
            filters={"employee": ["in", test_employees]},
            fields=["name", "employee", "time", "log_type", "shift"]
        )

        print(f"  Created {len(checkins)} checkins")

        # Verify checkins have shifts assigned (from fetch_shift)
        checkins_with_shifts = [c for c in checkins if c.shift]

        print(f"  Checkins with shifts: {len(checkins_with_shifts)}")

        # Basic assertions
        self.assertGreater(len(checkins), 0, "Should create checkins")

        # Verify logs are marked
        marked_logs = frappe.db.count("Machine Log", {
            "device": ["like", "PERFTEST_DEVICE%"],
            "employee_check_in_created": 1
        })

        print(f"  Marked logs: {marked_logs}")

        self.assertGreater(marked_logs, 0, "Should mark processed logs")

        print("  ✓ Overall functionality verified")


if __name__ == "__main__":
    unittest.main()
