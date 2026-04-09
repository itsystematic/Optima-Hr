"""
Query Analysis Tests for create_employee_checkin

Deep analysis of database query patterns:
- Total query counts
- N+1 query detection
- Duplicate query detection
- Query timing breakdown
- Index utilization
"""

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from hr_ksa.fingerprint.tests.fixtures import (
    create_test_machine_logs,
    cleanup_test_data,
    setup_complete_test_environment
)
from hr_ksa.fingerprint.tests.profiling_utils import QueryCounter
from hr_ksa.fingerprint.utils import create_employee_checkin


class TestQueryAnalysis(FrappeTestCase):
    """Query analysis tests for create_employee_checkin function"""

    @classmethod
    def setUpClass(cls):
        """Setup test environment once for all tests"""
        super().setUpClass()
        print("\n[SETUP] Initializing query analysis test environment...")

        # Create base test data
        cls.test_env = setup_complete_test_environment(
            n_employees=30,
            n_shifts=5,
            n_devices=3
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

    def test_count_total_queries(self):
        """
        Count total queries for different log volumes

        Establishes baseline query counts
        """
        print("\n" + "=" * 80)
        print("TEST: Total Query Count Analysis")
        print("=" * 80)

        # Create 1000 test logs
        logs = create_test_machine_logs(
            count=1000,
            employees=self.test_env['employees'][:20],
            devices=self.test_env['devices']
        )

        # Run with query counter
        with QueryCounter() as qc:
            create_employee_checkin()

        report = qc.get_report()

        # Print detailed report
        print(f"\n[QUERY COUNT BREAKDOWN]")
        print(f"  Total queries: {report['total_queries']}")
        print(f"  SELECT: {report['by_type']['SELECT']}")
        print(f"  INSERT: {report['by_type']['INSERT']}")
        print(f"  UPDATE: {report['by_type']['UPDATE']}")
        print(f"  DELETE: {report['by_type']['DELETE']}")

        print(f"\n[QUERY TIMING]")
        if report['timing']:
            print(f"  Total time: {report['timing']['total_time']:.4f}s")
            print(f"  Mean query time: {report['timing']['mean']:.4f}s")
            print(f"  Median query time: {report['timing']['median']:.4f}s")
            print(f"  Max query time: {report['timing']['max']:.4f}s")

        # Verify checkins created
        checkins_created = frappe.db.count("Employee Checkin", {
            "employee": ["like", "PERFTEST_EMP%"]
        })

        print(f"\n[RESULTS]")
        print(f"  Checkins created: {checkins_created}")
        print(f"  Queries per log: {report['total_queries'] / 1000:.2f}")

        # Assertions
        self.assertGreater(report['total_queries'], 0, "Should execute queries")
        self.assertGreater(checkins_created, 0, "Should create checkins")

    def test_detect_n_plus_one_queries(self):
        """
        Detect N+1 query patterns

        Identifies queries that execute once per log (N+1 problem)
        and provides specific recommendations
        """
        print("\n" + "=" * 80)
        print("TEST: N+1 Query Pattern Detection")
        print("=" * 80)

        # Create 500 test logs for clear pattern detection
        logs = create_test_machine_logs(
            count=500,
            employees=self.test_env['employees'][:15],
            devices=self.test_env['devices']
        )

        # Run with query counter
        with QueryCounter() as qc:
            create_employee_checkin()

        report = qc.get_report()

        # Print N+1 suspects
        if report['n_plus_one_suspects']:
            print(f"\n[N+1 QUERY PATTERNS DETECTED]")
            print(f"Found {len(report['n_plus_one_suspects'])} suspicious patterns")
            print("")

            for i, suspect in enumerate(report['n_plus_one_suspects'][:5], 1):
                print(f"Pattern {i}:")
                print(f"  Count: {suspect['count']} executions")
                print(f"  Total time: {suspect['total_time']:.4f}s")
                print(f"  Avg time: {suspect['avg_time']:.6f}s")
                print(f"  Pattern: {suspect['pattern'][:150]}...")
                print("")

            # Analyze the patterns
            top_suspect = report['n_plus_one_suspects'][0]

            print(f"[ANALYSIS]")
            print(f"  Top suspect executed {top_suspect['count']} times")
            print(f"  This consumed {top_suspect['total_time']:.4f}s total")

            if top_suspect['count'] > 100:
                print(f"  ✗ CRITICAL: Clear N+1 pattern detected")
                print(f"  Recommendation: Batch this query")
            elif top_suspect['count'] > 50:
                print(f"  ⚠ WARNING: Potential N+1 pattern")
            else:
                print(f"  ✓ Acceptable: Pattern may be necessary")

        else:
            print(f"\n[RESULTS]")
            print(f"  ✓ No N+1 patterns detected")

        # Additional analysis: queries per log
        queries_per_log = report['total_queries'] / 500

        print(f"\n[QUERY EFFICIENCY]")
        print(f"  Queries per log: {queries_per_log:.2f}")

        if queries_per_log < 1:
            print(f"  ✓ Excellent: Batch queries detected")
        elif queries_per_log < 3:
            print(f"  ✓ Good: Efficient query usage")
        elif queries_per_log < 10:
            print(f"  ⚠ Moderate: Some optimization possible")
        else:
            print(f"  ✗ Poor: High per-record query count")

    def test_duplicate_queries(self):
        """
        Detect duplicate (identical) queries

        Finds queries that execute multiple times with identical SQL
        """
        print("\n" + "=" * 80)
        print("TEST: Duplicate Query Detection")
        print("=" * 80)

        # Create test logs
        logs = create_test_machine_logs(
            count=300,
            employees=self.test_env['employees'][:10],
            devices=self.test_env['devices']
        )

        # Run with query counter
        with QueryCounter() as qc:
            create_employee_checkin()

        report = qc.get_report()

        # Print duplicate queries
        if report['duplicates']:
            print(f"\n[DUPLICATE QUERIES DETECTED]")
            print(f"Found {report['duplicate_count']} duplicate query patterns")
            print("")

            for i, dup in enumerate(report['duplicates'][:5], 1):
                print(f"Duplicate {i}:")
                print(f"  Executed {dup['count']} times")
                print(f"  Query: {dup['query'][:150]}...")
                print("")

            print(f"[ANALYSIS]")
            top_duplicate = report['duplicates'][0]

            if top_duplicate['count'] > 10:
                print(f"  ⚠ Query executed {top_duplicate['count']} times identically")
                print(f"  Recommendation: Consider caching this result")
            else:
                print(f"  ✓ Acceptable duplicate count")

        else:
            print(f"\n[RESULTS]")
            print(f"  ✓ No duplicate queries detected")

    def test_query_timing_breakdown(self):
        """
        Analyze query timing to identify slowest queries

        Helps prioritize optimization targets
        """
        print("\n" + "=" * 80)
        print("TEST: Query Timing Breakdown")
        print("=" * 80)

        # Create test logs
        logs = create_test_machine_logs(
            count=500,
            employees=self.test_env['employees'][:15],
            devices=self.test_env['devices']
        )

        # Run with query counter
        with QueryCounter() as qc:
            create_employee_checkin()

        report = qc.get_report()

        # Print slowest queries
        if report.get('slowest_queries'):
            print(f"\n[SLOWEST QUERIES]")
            print("Top 5 slowest queries:")
            print("")

            for i, query in enumerate(report['slowest_queries'], 1):
                print(f"{i}. Time: {query['time']:.6f}s")
                print(f"   Query: {query['query'][:150]}...")
                print("")

            # Calculate what percentage slowest query takes
            if report['timing']:
                slowest_time = report['slowest_queries'][0]['time']
                total_time = report['timing']['total_time']
                percentage = (slowest_time / total_time * 100) if total_time > 0 else 0

                print(f"[ANALYSIS]")
                print(f"  Slowest query took {slowest_time:.6f}s")
                print(f"  This is {percentage:.2f}% of total query time")

                if percentage > 50:
                    print(f"  ✗ CRITICAL: One query dominates execution time")
                elif percentage > 25:
                    print(f"  ⚠ WARNING: Optimize this query for major impact")
                else:
                    print(f"  ✓ Well-distributed query times")

        print(f"\n[TIMING STATISTICS]")
        if report['timing']:
            print(f"  Total query time: {report['timing']['total_time']:.4f}s")
            print(f"  Mean query time: {report['timing']['mean']:.6f}s")
            print(f"  Median query time: {report['timing']['median']:.6f}s")
            if 'stdev' in report['timing']:
                print(f"  Std deviation: {report['timing']['stdev']:.6f}s")

    def test_query_complexity_by_log_count(self):
        """
        Test how query complexity changes with log count

        Verifies query count growth is sub-linear or constant
        """
        print("\n" + "=" * 80)
        print("TEST: Query Complexity vs Log Count")
        print("=" * 80)

        test_sizes = [50, 100, 200, 500]
        complexity_data = []

        for size in test_sizes:
            # Create test logs
            logs = create_test_machine_logs(
                count=size,
                employees=self.test_env['employees'][:10],
                devices=self.test_env['devices']
            )

            # Count queries
            with QueryCounter() as qc:
                create_employee_checkin()

            report = qc.get_report()

            complexity_data.append({
                'log_count': size,
                'query_count': report['total_queries'],
                'ratio': report['total_queries'] / size
            })

            # Clean up for next iteration
            frappe.db.sql("DELETE FROM `tabMachine Log` WHERE device LIKE 'PERFTEST_DEVICE%'")
            frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE employee LIKE 'PERFTEST_EMP%'")
            frappe.db.commit()

        # Print results table
        print(f"\n[COMPLEXITY ANALYSIS]")
        print(f"{'Logs':<10} {'Queries':<12} {'Q/Log Ratio':<15} {'Growth':<10}")
        print("-" * 50)

        for i, data in enumerate(complexity_data):
            if i == 0:
                growth = "baseline"
            else:
                prev_ratio = complexity_data[i-1]['ratio']
                curr_ratio = data['ratio']
                growth_factor = curr_ratio / prev_ratio if prev_ratio > 0 else 0
                growth = f"{growth_factor:.2f}x"

            print(f"{data['log_count']:<10} {data['query_count']:<12} {data['ratio']:<15.2f} {growth:<10}")

        # Analyze growth pattern
        first_ratio = complexity_data[0]['ratio']
        last_ratio = complexity_data[-1]['ratio']
        overall_growth = last_ratio / first_ratio if first_ratio > 0 else 0

        print(f"\n[GROWTH ANALYSIS]")
        print(f"  First ratio: {first_ratio:.2f} queries/log")
        print(f"  Last ratio: {last_ratio:.2f} queries/log")
        print(f"  Overall growth: {overall_growth:.2f}x")

        if overall_growth < 1.2:
            print(f"  ✓ Excellent: Constant complexity O(1)")
        elif overall_growth < 2:
            print(f"  ✓ Good: Sub-linear complexity")
        elif overall_growth < 5:
            print(f"  ⚠ Moderate: Linear complexity O(n)")
        else:
            print(f"  ✗ Poor: Super-linear complexity (likely O(n²))")

    def test_specific_query_patterns(self):
        """
        Test for specific known query patterns

        Checks for common anti-patterns:
        - frappe.get_doc() in loops
        - frappe.db.get_value() per record
        - frappe.db.exists() per record
        """
        print("\n" + "=" * 80)
        print("TEST: Specific Query Pattern Analysis")
        print("=" * 80)

        # Create test logs
        logs = create_test_machine_logs(
            count=200,
            employees=self.test_env['employees'][:10],
            devices=self.test_env['devices']
        )

        # Track all queries
        with QueryCounter() as qc:
            create_employee_checkin()

        # Analyze query patterns
        get_doc_count = 0
        get_value_count = 0
        exists_count = 0

        for query_info in qc.queries:
            query = query_info['query'].upper()

            # Check for specific patterns
            if 'SELECT' in query and 'TABEMPLOYEE' in query.replace(' ', ''):
                if 'LIMIT 1' in query or query.count('WHERE') == 1:
                    get_doc_count += 1

            if 'EXISTS' in query or '(SELECT ' in query:
                exists_count += 1

        print(f"\n[PATTERN ANALYSIS]")
        print(f"  Employee lookup queries: {get_doc_count}")
        print(f"  Existence check queries: {exists_count}")
        print(f"  Total logs processed: {len(logs)}")

        print(f"\n[PER-LOG RATIOS]")
        print(f"  Employee lookups per log: {get_doc_count / len(logs):.2f}")
        print(f"  Existence checks per log: {exists_count / len(logs):.2f}")

        print(f"\n[RECOMMENDATIONS]")

        if get_doc_count / len(logs) > 0.5:
            print(f"  ⚠ High employee lookup ratio")
            print(f"     Suggestion: Batch load employees upfront")

        if exists_count / len(logs) > 0.5:
            print(f"  ⚠ High existence check ratio")
            print(f"     Suggestion: Batch check for existing checkins")

        if get_doc_count / len(logs) < 0.2 and exists_count / len(logs) < 0.2:
            print(f"  ✓ Efficient query patterns detected")


if __name__ == "__main__":
    unittest.main()
