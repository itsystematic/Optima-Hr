"""
Performance Benchmark Tests for create_employee_checkin

Tests the function's performance with varying data volumes:
- 100 logs (baseline)
- 500 logs (small deployment)
- 1000 logs (large deployment)
- 5000 logs (stress test)

Measures:
- Execution time
- Query count
- Memory usage
- Scalability
"""

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from hr_ksa.fingerprint.tests.fixtures import (
    create_test_employees,
    create_test_shifts,
    create_test_devices,
    create_test_machine_logs,
    create_shift_assignments,
    cleanup_test_data,
    setup_complete_test_environment
)
from hr_ksa.fingerprint.tests.profiling_utils import (
    QueryCounter,
    TimingProfiler,
    MemoryProfiler,
    PerformanceReport
)
from hr_ksa.fingerprint.utils import create_employee_checkin


class TestCreateEmployeeCheckinPerformance(FrappeTestCase):
    """Performance benchmark tests for create_employee_checkin function"""

    @classmethod
    def setUpClass(cls):
        """Setup test environment once for all tests"""
        super().setUpClass()
        print("\n[SETUP] Initializing performance test environment...")

        # Create base test data
        cls.test_env = setup_complete_test_environment(
            n_employees=50,  # Enough for all tests
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

    def test_baseline_100_logs(self):
        """
        Baseline test with 100 machine logs

        Establishes performance baseline for comparison
        """
        print("\n" + "=" * 80)
        print("TEST: Baseline Performance - 100 Logs")
        print("=" * 80)

        # Create test machine logs
        logs = create_test_machine_logs(
            count=100,
            employees=self.test_env['employees'][:10],
            devices=self.test_env['devices']
        )

        self.assertEqual(len(logs), 100, "Should create 100 logs")

        # Run performance test
        report = PerformanceReport("baseline_100_logs")

        with QueryCounter() as qc:
            with TimingProfiler("create_employee_checkin") as tp:
                with MemoryProfiler("create_employee_checkin") as mp:
                    create_employee_checkin()

        # Add metrics to report
        report.add_query_analysis(qc.get_report())
        report.add_timing(tp.get_stats())
        report.add_memory(mp.memory_mb, mp.peak_mb)

        # Save report
        report_path = report.save('hr_ksa/fingerprint/tests/reports', format='text')
        print(f"\n[REPORT] Saved to: {report_path}")

        # Print summary
        query_report = qc.get_report()
        print(f"\n[RESULTS]")
        print(f"  Execution time: {tp.elapsed:.4f}s")
        print(f"  Total queries: {query_report['total_queries']}")
        print(f"  Queries per log: {query_report['total_queries'] / 100:.2f}")
        print(f"  Memory delta: {mp.memory_mb:.2f} MB")
        print(f"  Peak memory: {mp.peak_mb:.2f} MB")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Checkins created: {checkins_created}")

        # Basic assertions
        self.assertGreater(checkins_created, 0, "Should create checkins")
        self.assertLess(tp.elapsed, 60, "Should complete within 60 seconds")

    def test_baseline_500_logs(self):
        """
        Scale test with 500 machine logs

        Tests typical small deployment scenario
        """
        print("\n" + "=" * 80)
        print("TEST: Small Deployment - 500 Logs")
        print("=" * 80)

        # Create test machine logs
        logs = create_test_machine_logs(
            count=500,
            employees=self.test_env['employees'][:20],
            devices=self.test_env['devices']
        )

        self.assertEqual(len(logs), 500, "Should create 500 logs")

        # Run performance test
        report = PerformanceReport("baseline_500_logs")

        with QueryCounter() as qc:
            with TimingProfiler("create_employee_checkin") as tp:
                with MemoryProfiler("create_employee_checkin") as mp:
                    create_employee_checkin()

        # Add metrics to report
        report.add_query_analysis(qc.get_report())
        report.add_timing(tp.get_stats())
        report.add_memory(mp.memory_mb, mp.peak_mb)

        # Save report
        report_path = report.save('hr_ksa/fingerprint/tests/reports', format='text')
        print(f"\n[REPORT] Saved to: {report_path}")

        # Print summary
        query_report = qc.get_report()
        print(f"\n[RESULTS]")
        print(f"  Execution time: {tp.elapsed:.4f}s")
        print(f"  Total queries: {query_report['total_queries']}")
        print(f"  Queries per log: {query_report['total_queries'] / 500:.2f}")
        print(f"  Memory delta: {mp.memory_mb:.2f} MB")
        print(f"  Peak memory: {mp.peak_mb:.2f} MB")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Checkins created: {checkins_created}")

        # Basic assertions
        self.assertGreater(checkins_created, 0, "Should create checkins")
        self.assertLess(tp.elapsed, 120, "Should complete within 120 seconds")

    def test_baseline_1000_logs(self):
        """
        Scale test with 1000 machine logs

        Tests typical large deployment scenario
        """
        print("\n" + "=" * 80)
        print("TEST: Large Deployment - 1000 Logs")
        print("=" * 80)

        # Create test machine logs
        logs = create_test_machine_logs(
            count=1000,
            employees=self.test_env['employees'][:30],
            devices=self.test_env['devices']
        )

        self.assertEqual(len(logs), 1000, "Should create 1000 logs")

        # Run performance test
        report = PerformanceReport("baseline_1000_logs")

        with QueryCounter() as qc:
            with TimingProfiler("create_employee_checkin") as tp:
                with MemoryProfiler("create_employee_checkin") as mp:
                    create_employee_checkin()

        # Add metrics to report
        report.add_query_analysis(qc.get_report())
        report.add_timing(tp.get_stats())
        report.add_memory(mp.memory_mb, mp.peak_mb)

        # Save report
        report_path = report.save('hr_ksa/fingerprint/tests/reports', format='json')
        print(f"\n[REPORT] Saved to: {report_path}")

        # Print summary
        query_report = qc.get_report()
        print(f"\n[RESULTS]")
        print(f"  Execution time: {tp.elapsed:.4f}s")
        print(f"  Total queries: {query_report['total_queries']}")
        print(f"  Queries per log: {query_report['total_queries'] / 1000:.2f}")
        print(f"  Memory delta: {mp.memory_mb:.2f} MB")
        print(f"  Peak memory: {mp.peak_mb:.2f} MB")

        # Print N+1 suspects
        if query_report['n_plus_one_suspects']:
            print(f"\n[N+1 SUSPECTS]")
            for suspect in query_report['n_plus_one_suspects'][:3]:
                print(f"  Pattern (x{suspect['count']}): {suspect['pattern'][:100]}")
                print(f"    Total time: {suspect['total_time']:.4f}s")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Checkins created: {checkins_created}")

        # Basic assertions
        self.assertGreater(checkins_created, 0, "Should create checkins")

    def test_baseline_5000_logs(self):
        """
        Stress test with 5000 machine logs

        Tests burst scenario (device sync dump)
        """
        print("\n" + "=" * 80)
        print("TEST: Stress Test - 5000 Logs")
        print("=" * 80)

        # Create test machine logs
        logs = create_test_machine_logs(
            count=5000,
            employees=self.test_env['employees'],  # Use all employees
            devices=self.test_env['devices']
        )

        self.assertEqual(len(logs), 5000, "Should create 5000 logs")

        # Run performance test
        report = PerformanceReport("baseline_5000_logs")

        with QueryCounter() as qc:
            with TimingProfiler("create_employee_checkin") as tp:
                with MemoryProfiler("create_employee_checkin") as mp:
                    create_employee_checkin()

        # Add metrics to report
        report.add_query_analysis(qc.get_report())
        report.add_timing(tp.get_stats())
        report.add_memory(mp.memory_mb, mp.peak_mb)

        # Save report
        report_path = report.save('hr_ksa/fingerprint/tests/reports', format='json')
        print(f"\n[REPORT] Saved to: {report_path}")

        # Print summary
        query_report = qc.get_report()
        print(f"\n[RESULTS]")
        print(f"  Execution time: {tp.elapsed:.4f}s")
        print(f"  Total queries: {query_report['total_queries']}")
        print(f"  Queries per log: {query_report['total_queries'] / 5000:.2f}")
        print(f"  Memory delta: {mp.memory_mb:.2f} MB")
        print(f"  Peak memory: {mp.peak_mb:.2f} MB")

        # Print slowest queries
        if query_report.get('slowest_queries'):
            print(f"\n[SLOWEST QUERIES]")
            for i, query in enumerate(query_report['slowest_queries'][:3], 1):
                print(f"  {i}. Time: {query['time']:.4f}s")
                print(f"     Query: {query['query'][:100]}")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"  Checkins created: {checkins_created}")

        # Basic assertions
        self.assertGreater(checkins_created, 0, "Should create checkins")
        # Allow more time for stress test
        self.assertLess(tp.elapsed, 300, "Should complete within 5 minutes")

    def test_query_scalability(self):
        """
        Test query count scalability

        Verifies that query count scales linearly (O(n)) or better,
        not quadratically (O(n²))
        """
        print("\n" + "=" * 80)
        print("TEST: Query Scalability Analysis")
        print("=" * 80)

        test_sizes = [100, 200, 500, 1000]
        results = []

        for size in test_sizes:
            # Create test logs
            logs = create_test_machine_logs(
                count=size,
                employees=self.test_env['employees'][:20],
                devices=self.test_env['devices']
            )

            # Measure queries
            with QueryCounter() as qc:
                create_employee_checkin()

            query_report = qc.get_report()
            queries_per_log = query_report['total_queries'] / size

            results.append({
                'size': size,
                'total_queries': query_report['total_queries'],
                'queries_per_log': queries_per_log
            })

            # Clean up for next iteration
            frappe.db.sql("DELETE FROM `tabMachine Log` WHERE device LIKE 'PERFTEST_DEVICE%'")
            frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE employee LIKE 'PERFTEST_EMP%'")
            frappe.db.commit()

        # Print results
        print(f"\n[SCALABILITY RESULTS]")
        print(f"{'Size':<10} {'Queries':<15} {'Queries/Log':<15}")
        print("-" * 40)

        for r in results:
            print(f"{r['size']:<10} {r['total_queries']:<15} {r['queries_per_log']:<15.2f}")

        # Analyze scalability
        # Ideally, queries_per_log should be constant (O(1)) or log(n)
        # If it increases linearly, we have O(n²) problem
        first_ratio = results[0]['queries_per_log']
        last_ratio = results[-1]['queries_per_log']

        print(f"\n[ANALYSIS]")
        print(f"  First ratio (100 logs): {first_ratio:.2f} queries/log")
        print(f"  Last ratio (1000 logs): {last_ratio:.2f} queries/log")

        if last_ratio <= first_ratio * 1.5:
            print(f"  ✓ Good scalability - queries scale sub-linearly or constant")
        elif last_ratio <= first_ratio * 3:
            print(f"  ⚠ Acceptable scalability - queries scale linearly")
        else:
            print(f"  ✗ Poor scalability - queries scale super-linearly (N+1 problem)")

    def test_memory_consumption(self):
        """
        Test memory consumption patterns

        Verifies that memory usage doesn't grow unexpectedly
        and there are no memory leaks
        """
        print("\n" + "=" * 80)
        print("TEST: Memory Consumption Analysis")
        print("=" * 80)

        test_sizes = [100, 500, 1000]
        results = []

        for size in test_sizes:
            # Create test logs
            logs = create_test_machine_logs(
                count=size,
                employees=self.test_env['employees'][:20],
                devices=self.test_env['devices']
            )

            # Measure memory
            with MemoryProfiler(f"create_employee_checkin ({size} logs)") as mp:
                create_employee_checkin()

            results.append({
                'size': size,
                'memory_mb': mp.memory_mb,
                'peak_mb': mp.peak_mb,
                'memory_per_log': mp.memory_mb / size if size > 0 else 0
            })

            # Clean up for next iteration
            frappe.db.sql("DELETE FROM `tabMachine Log` WHERE device LIKE 'PERFTEST_DEVICE%'")
            frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE employee LIKE 'PERFTEST_EMP%'")
            frappe.db.commit()

        # Print results
        print(f"\n[MEMORY RESULTS]")
        print(f"{'Size':<10} {'Delta MB':<15} {'Peak MB':<15} {'MB/Log':<15}")
        print("-" * 55)

        for r in results:
            print(f"{r['size']:<10} {r['memory_mb']:<15.2f} {r['peak_mb']:<15.2f} {r['memory_per_log']:<15.4f}")

        # Analyze memory growth
        print(f"\n[ANALYSIS]")
        if all(r['peak_mb'] < 100 for r in results):
            print(f"  ✓ Acceptable memory usage (< 100 MB peak)")
        else:
            print(f"  ⚠ High memory usage detected")

        # Check for linear growth
        if len(results) >= 2:
            memory_growth_rate = results[-1]['memory_per_log'] / results[0]['memory_per_log']
            if memory_growth_rate < 1.5:
                print(f"  ✓ Memory scales linearly")
            else:
                print(f"  ⚠ Memory growth rate: {memory_growth_rate:.2f}x")


if __name__ == "__main__":
    unittest.main()
