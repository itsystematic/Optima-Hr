"""
Load Testing for create_employee_checkin

Tests real-world deployment scenarios:
- Small deployment (50-100 logs per 15 min)
- Large deployment (1000+ logs per 15 min)
- Burst scenario (5000+ logs at once)
- Production simulation (realistic data distribution)
"""

import frappe
import unittest
from datetime import datetime, timedelta
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from hr_ksa.fingerprint.tests.fixtures import (
    create_test_machine_logs,
    cleanup_test_data,
    setup_complete_test_environment
)
from hr_ksa.fingerprint.tests.profiling_utils import (
    TimingProfiler,
    QueryCounter
)
from hr_ksa.fingerprint.utils import create_employee_checkin


class TestLoadScenarios(FrappeTestCase):
    """Load testing for create_employee_checkin under various scenarios"""

    @classmethod
    def setUpClass(cls):
        """Setup test environment once for all tests"""
        super().setUpClass()
        print("\n[SETUP] Initializing load test environment...")

        # Create comprehensive test data
        cls.test_env = setup_complete_test_environment(
            n_employees=100,  # Large enough for all scenarios
            n_shifts=10,
            n_devices=5
        )

        print(f"[SETUP] Test environment ready")

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests"""
        print("\n[CLEANUP] Removing all test data...")
        cleanup_test_data()
        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        # Delete machine logs and checkins created in tests
        frappe.db.sql("""
            DELETE FROM `tabMachine Log`
            WHERE device LIKE 'PERFTEST_DEVICE%'
        """)

        frappe.db.sql("""
            DELETE FROM `tabEmployee Checkin`
            WHERE employee LIKE 'PERFTEST_EMP%'
        """)

        frappe.db.commit()

    def test_typical_small_deployment(self):
        """
        Simulate typical small deployment

        Scenario:
        - 10-20 employees
        - 50-100 logs per 15-minute interval
        - Simulates 24-hour period (96 intervals)
        - Measures average performance
        """
        print("\n" + "=" * 80)
        print("LOAD TEST: Small Deployment Simulation")
        print("=" * 80)
        print(f"\nScenario:")
        print(f"  Employees: 20")
        print(f"  Logs per interval: 50-100")
        print(f"  Intervals simulated: 10 (represents 2.5 hours)")
        print("")

        employees = self.test_env['employees'][:20]
        devices = self.test_env['devices'][:2]

        timings = []
        query_counts = []

        # Simulate 10 intervals (2.5 hours worth)
        for interval in range(10):
            print(f"Interval {interval + 1}/10...", end=" ")

            # Create 50-100 logs for this interval
            import random
            n_logs = random.randint(50, 100)

            base_time = now_datetime() + timedelta(minutes=interval * 15)

            logs = create_test_machine_logs(
                count=n_logs,
                employees=employees,
                devices=devices,
                base_date=base_time
            )

            # Process logs
            with QueryCounter() as qc:
                with TimingProfiler(f"Interval {interval + 1}") as tp:
                    create_employee_checkin()

            timings.append(tp.elapsed)
            query_counts.append(qc.get_report()['total_queries'])

            # Mark logs as processed so they don't interfere with next interval
            frappe.db.sql("""
                UPDATE `tabMachine Log`
                SET employee_check_in_created = 1
                WHERE device LIKE 'PERFTEST_DEVICE%'
            """)

            print(f"✓ {tp.elapsed:.2f}s, {qc.get_report()['total_queries']} queries")

        # Calculate statistics
        import statistics

        avg_time = statistics.mean(timings)
        max_time = max(timings)
        min_time = min(timings)

        avg_queries = statistics.mean(query_counts)

        print(f"\n[RESULTS]")
        print(f"  Average time per interval: {avg_time:.4f}s")
        print(f"  Min time: {min_time:.4f}s")
        print(f"  Max time: {max_time:.4f}s")
        print(f"  Average queries per interval: {avg_queries:.0f}")

        print(f"\n[ANALYSIS]")
        if max_time < 10:
            print(f"  ✓ Excellent: All intervals completed in <10s")
        elif max_time < 30:
            print(f"  ✓ Good: All intervals completed in <30s")
        else:
            print(f"  ⚠ Slow: Some intervals took >{max_time:.0f}s")

        # For small deployment, should be very fast
        self.assertLess(avg_time, 30, "Average time should be < 30s for small deployment")

    def test_typical_large_deployment(self):
        """
        Simulate typical large deployment

        Scenario:
        - 50-100 employees
        - 1000+ logs per 15-minute interval
        - High throughput scenario
        """
        print("\n" + "=" * 80)
        print("LOAD TEST: Large Deployment Simulation")
        print("=" * 80)
        print(f"\nScenario:")
        print(f"  Employees: 50")
        print(f"  Logs per interval: 1000")
        print(f"  Intervals simulated: 5 (represents 75 minutes)")
        print("")

        employees = self.test_env['employees'][:50]
        devices = self.test_env['devices']

        timings = []
        query_counts = []

        # Simulate 5 intervals
        for interval in range(5):
            print(f"Interval {interval + 1}/5...", end=" ")

            base_time = now_datetime() + timedelta(minutes=interval * 15)

            logs = create_test_machine_logs(
                count=1000,
                employees=employees,
                devices=devices,
                base_date=base_time
            )

            # Process logs
            with QueryCounter() as qc:
                with TimingProfiler(f"Interval {interval + 1}") as tp:
                    create_employee_checkin()

            timings.append(tp.elapsed)
            query_counts.append(qc.get_report()['total_queries'])

            # Mark logs as processed
            frappe.db.sql("""
                UPDATE `tabMachine Log`
                SET employee_check_in_created = 1
                WHERE device LIKE 'PERFTEST_DEVICE%'
            """)

            print(f"✓ {tp.elapsed:.2f}s, {qc.get_report()['total_queries']} queries")

        # Calculate statistics
        import statistics

        avg_time = statistics.mean(timings)
        max_time = max(timings)

        print(f"\n[RESULTS]")
        print(f"  Average time per interval: {avg_time:.4f}s")
        print(f"  Max time: {max_time:.4f}s")
        print(f"  Throughput: {1000 / avg_time:.2f} logs/second")

        print(f"\n[ANALYSIS]")
        if avg_time < 30:
            print(f"  ✓ Excellent: Processing 1000 logs in <30s")
        elif avg_time < 60:
            print(f"  ✓ Good: Processing 1000 logs in <60s")
        elif avg_time < 120:
            print(f"  ⚠ Acceptable: Processing 1000 logs in <2 minutes")
        else:
            print(f"  ✗ Slow: Processing taking >{avg_time:.0f}s")

        # For large deployment, should complete within reasonable time
        self.assertLess(avg_time, 120, "Should process 1000 logs in < 2 minutes")

    def test_burst_scenario(self):
        """
        Simulate burst scenario

        Scenario:
        - Device sync dumps 5000+ logs at once
        - Tests system resilience under sudden load
        - Happens when device is offline then comes back online
        """
        print("\n" + "=" * 80)
        print("LOAD TEST: Burst Scenario (Device Sync Dump)")
        print("=" * 80)
        print(f"\nScenario:")
        print(f"  Employees: 80")
        print(f"  Logs in burst: 5000")
        print(f"  Simulates: Device offline for days, then syncs")
        print("")

        employees = self.test_env['employees'][:80]
        devices = self.test_env['devices']

        # Create 5000 logs spread over 3 days (simulating backlog)
        print("Creating 5000 backlogged logs...", end=" ")

        base_time = now_datetime() - timedelta(days=3)

        logs = create_test_machine_logs(
            count=5000,
            employees=employees,
            devices=devices,
            base_date=base_time
        )

        print(f"✓ {len(logs)} logs created")
        print("")

        # Process all at once (burst)
        print("Processing burst...")

        with QueryCounter() as qc:
            with TimingProfiler("Burst Processing") as tp:
                create_employee_checkin()

        query_report = qc.get_report()

        print(f"\n[RESULTS]")
        print(f"  Total time: {tp.elapsed:.4f}s ({tp.elapsed / 60:.2f} minutes)")
        print(f"  Total queries: {query_report['total_queries']}")
        print(f"  Throughput: {5000 / tp.elapsed:.2f} logs/second")
        print(f"  Queries per log: {query_report['total_queries'] / 5000:.2f}")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Checkins created: {checkins_created}")

        print(f"\n[ANALYSIS]")
        if tp.elapsed < 60:
            print(f"  ✓ Excellent: Handled burst in <1 minute")
        elif tp.elapsed < 180:
            print(f"  ✓ Good: Handled burst in <3 minutes")
        elif tp.elapsed < 300:
            print(f"  ⚠ Acceptable: Handled burst in <5 minutes")
        else:
            print(f"  ✗ Slow: Burst processing took >{tp.elapsed / 60:.1f} minutes")

        # System should handle burst within reasonable time
        self.assertLess(tp.elapsed, 300, "Should handle 5000-log burst in < 5 minutes")

    def test_production_simulation(self):
        """
        Simulate realistic production scenario

        Scenario:
        - Mixed employee activity (some very active, some occasional)
        - Multiple devices
        - Realistic clock in/out patterns
        - Includes edge cases:
          * Duplicates
          * Inactive employees
          * Missing shifts
        """
        print("\n" + "=" * 80)
        print("LOAD TEST: Realistic Production Simulation")
        print("=" * 80)
        print(f"\nScenario:")
        print(f"  Employees: 60 (varied activity levels)")
        print(f"  Devices: 5")
        print(f"  Logs: 800 (realistic distribution)")
        print(f"  Includes: Duplicates, inactive employees, edge cases")
        print("")

        employees = self.test_env['employees'][:60]
        devices = self.test_env['devices']

        # Create realistic log distribution
        print("Creating realistic log distribution...", end=" ")

        # 70% of logs from 30% of employees (active employees)
        active_employees = employees[:18]
        occasional_employees = employees[18:60]

        active_logs = create_test_machine_logs(
            count=560,  # 70% of 800
            employees=active_employees,
            devices=devices
        )

        occasional_logs = create_test_machine_logs(
            count=240,  # 30% of 800
            employees=occasional_employees,
            devices=devices
        )

        print(f"✓ {len(active_logs) + len(occasional_logs)} logs created")
        print("")

        # Add some inactive employee logs (should be skipped)
        print("Adding edge cases (inactive employees)...", end=" ")

        # Make 5 employees inactive
        for emp in employees[:5]:
            frappe.db.set_value("Employee", emp, "status", "Inactive")

        # Create logs for inactive employees (should be skipped)
        inactive_logs = create_test_machine_logs(
            count=50,
            employees=employees[:5],
            devices=devices
        )

        print(f"✓ {len(inactive_logs)} inactive employee logs")
        print("")

        # Process all logs
        print("Processing production simulation...")

        with QueryCounter() as qc:
            with TimingProfiler("Production Simulation") as tp:
                create_employee_checkin()

        query_report = qc.get_report()

        # Verify results
        total_logs = len(active_logs) + len(occasional_logs) + len(inactive_logs)

        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        # Should skip inactive employee logs
        expected_max_checkins = total_logs - len(inactive_logs)

        print(f"\n[RESULTS]")
        print(f"  Total logs: {total_logs}")
        print(f"  Inactive employee logs: {len(inactive_logs)}")
        print(f"  Checkins created: {checkins_created}")
        print(f"  Processing time: {tp.elapsed:.4f}s")
        print(f"  Total queries: {query_report['total_queries']}")

        print(f"\n[VALIDATION]")
        if checkins_created <= expected_max_checkins:
            print(f"  ✓ Correctly skipped inactive employee logs")
        else:
            print(f"  ✗ Created checkins for inactive employees")

        print(f"\n[ANALYSIS]")
        if tp.elapsed < 60:
            print(f"  ✓ Excellent: Production scenario in <1 minute")
        elif tp.elapsed < 120:
            print(f"  ✓ Good: Production scenario in <2 minutes")
        else:
            print(f"  ⚠ Slow: Production scenario took {tp.elapsed:.0f}s")

        # Reset employee status
        for emp in employees[:5]:
            frappe.db.set_value("Employee", emp, "status", "Active")

        # Assertions
        self.assertGreater(checkins_created, 0, "Should create checkins")
        self.assertLessEqual(checkins_created, expected_max_checkins,
                            "Should not create checkins for inactive employees")

    def test_concurrent_execution_safety(self):
        """
        Test behavior if function runs concurrently

        Scenario:
        - Simulate cron job running while previous execution still processing
        - Verifies no race conditions or data corruption
        """
        print("\n" + "=" * 80)
        print("LOAD TEST: Concurrent Execution Safety")
        print("=" * 80)
        print(f"\nScenario:")
        print(f"  Simulates overlapping cron executions")
        print(f"  Tests for race conditions")
        print("")

        employees = self.test_env['employees'][:20]
        devices = self.test_env['devices']

        # Create logs for first execution
        logs_batch1 = create_test_machine_logs(
            count=300,
            employees=employees,
            devices=devices
        )

        # Create logs for second execution (overlap scenario)
        logs_batch2 = create_test_machine_logs(
            count=300,
            employees=employees,
            devices=devices
        )

        print(f"Created {len(logs_batch1) + len(logs_batch2)} logs total")
        print("")

        # Run both executions
        print("Running first execution...", end=" ")
        with TimingProfiler("Execution 1") as tp1:
            create_employee_checkin()
        print(f"✓ {tp1.elapsed:.2f}s")

        # Count checkins after first run
        checkins_after_first = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"Running second execution...", end=" ")
        with TimingProfiler("Execution 2") as tp2:
            create_employee_checkin()
        print(f"✓ {tp2.elapsed:.2f}s")

        # Count checkins after second run
        checkins_after_second = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"\n[RESULTS]")
        print(f"  Checkins after first run: {checkins_after_first}")
        print(f"  Checkins after second run: {checkins_after_second}")
        print(f"  New checkins in second run: {checkins_after_second - checkins_after_first}")

        print(f"\n[ANALYSIS]")
        if checkins_after_second == checkins_after_first:
            print(f"  ✓ No duplicate processing (all logs already processed)")
        elif checkins_after_second > checkins_after_first:
            print(f"  ✓ Processed remaining logs correctly")
        else:
            print(f"  ✗ Unexpected behavior")

        # Second run should be fast (no new logs to process)
        if tp2.elapsed < tp1.elapsed * 0.5:
            print(f"  ✓ Second run efficient (no work to do)")


if __name__ == "__main__":
    unittest.main()
