"""
Profiling Runner - CLI Tool for Comprehensive Performance Analysis

Provides a command-line interface to run detailed profiling of create_employee_checkin:
- Line-by-line profiling with cProfile
- Query counting and analysis
- Memory profiling
- Timing breakdowns
- Report generation

Usage:
    bench --site [site-name] execute hr_ksa.fingerprint.tests.run_profiling.profile_create_employee_checkin --kwargs "{'n_logs': 1000}"
"""

import frappe
import cProfile
import pstats
import io
import os
from datetime import datetime
from hr_ksa.fingerprint.tests.fixtures import (
    create_test_machine_logs,
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


def profile_create_employee_checkin(n_logs=1000, generate_reports=True):
    """
    Execute comprehensive profiling of create_employee_checkin

    Args:
        n_logs: Number of machine logs to create for testing
        generate_reports: Whether to generate and save report files

    Returns:
        dict: Summary of profiling results
    """
    print("=" * 80)
    print(f"COMPREHENSIVE PROFILING: create_employee_checkin ({n_logs} logs)")
    print("=" * 80)
    print("")

    # Setup test environment
    print("[STEP 1/6] Setting up test environment...")
    test_env = setup_complete_test_environment(
        n_employees=max(20, n_logs // 50),
        n_shifts=10,
        n_devices=5
    )

    print(f"  ✓ Created {len(test_env['employees'])} employees")
    print(f"  ✓ Created {len(test_env['shifts'])} shifts")
    print(f"  ✓ Created {len(test_env['devices'])} devices")
    print("")

    # Create test machine logs
    print(f"[STEP 2/6] Creating {n_logs} test machine logs...")
    logs = create_test_machine_logs(
        count=n_logs,
        employees=test_env['employees'],
        devices=test_env['devices']
    )

    print(f"  ✓ Created {len(logs)} machine logs")
    print("")

    # Initialize result storage
    results = {
        'n_logs': n_logs,
        'timestamp': datetime.now().isoformat(),
        'profiling': {},
        'queries': {},
        'timing': {},
        'memory': {}
    }

    # STEP 3: Query Analysis
    print("[STEP 3/6] Running query analysis...")
    with QueryCounter() as qc:
        with TimingProfiler("Query Analysis") as tp_query:
            create_employee_checkin()

    query_report = qc.get_report()
    results['queries'] = query_report
    results['timing']['with_query_tracking'] = tp_query.elapsed

    print(f"  ✓ Executed {query_report['total_queries']} total queries")
    print(f"  ✓ Execution time: {tp_query.elapsed:.4f}s")
    print("")

    # Clean up for next profiling run
    _cleanup_created_checkins()

    # Create logs again for cProfile run
    logs = create_test_machine_logs(
        count=n_logs,
        employees=test_env['employees'],
        devices=test_env['devices']
    )

    # STEP 4: cProfile Line-by-Line Profiling
    print("[STEP 4/6] Running cProfile line-by-line profiling...")

    profiler = cProfile.Profile()
    profiler.enable()

    create_employee_checkin()

    profiler.disable()

    # Get profiling stats
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.strip_dirs()
    stats.sort_stats('cumulative')

    print(f"  ✓ Profiling complete")
    print("")

    # Clean up for memory profiling
    _cleanup_created_checkins()

    # Create logs again for memory profiling
    logs = create_test_machine_logs(
        count=n_logs,
        employees=test_env['employees'],
        devices=test_env['devices']
    )

    # STEP 5: Memory Profiling
    print("[STEP 5/6] Running memory profiling...")
    with MemoryProfiler("create_employee_checkin") as mp:
        with TimingProfiler("Memory Analysis") as tp_mem:
            create_employee_checkin()

    results['memory'] = {
        'delta_mb': mp.memory_mb,
        'peak_mb': mp.peak_mb
    }

    results['timing']['with_memory_tracking'] = tp_mem.elapsed

    print(f"  ✓ Memory delta: {mp.memory_mb:.2f} MB")
    print(f"  ✓ Peak memory: {mp.peak_mb:.2f} MB")
    print("")

    # STEP 6: Generate Reports
    if generate_reports:
        print("[STEP 6/6] Generating reports...")

        # Ensure reports directory exists
        reports_dir = 'hr_ksa/fingerprint/tests/reports'
        os.makedirs(reports_dir, exist_ok=True)

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. cProfile Report
        profile_report_path = f"{reports_dir}/profiling_report_{timestamp_str}.txt"
        with open(profile_report_path, 'w') as f:
            stats = pstats.Stats(profiler, stream=f)
            stats.strip_dirs()
            stats.sort_stats('cumulative')
            stats.print_stats(50)  # Top 50 functions

        print(f"  ✓ Saved cProfile report: {profile_report_path}")

        # 2. Query Analysis Report (JSON)
        import json
        query_report_path = f"{reports_dir}/query_analysis_{timestamp_str}.json"
        with open(query_report_path, 'w') as f:
            json.dump(query_report, f, indent=2, default=str)

        print(f"  ✓ Saved query analysis: {query_report_path}")

        # 3. Memory Profile Report
        memory_report_path = f"{reports_dir}/memory_profile_{timestamp_str}.txt"
        with open(memory_report_path, 'w') as f:
            f.write(f"Memory Profile Report\n")
            f.write(f"=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Test size: {n_logs} logs\n")
            f.write(f"\n")
            f.write(f"Memory Delta: {mp.memory_mb:.2f} MB\n")
            f.write(f"Peak Memory: {mp.peak_mb:.2f} MB\n")
            f.write(f"Memory per log: {mp.memory_mb / n_logs:.6f} MB\n")

        print(f"  ✓ Saved memory profile: {memory_report_path}")

        # 4. Comprehensive Summary Report
        summary_report = PerformanceReport(f"profiling_{n_logs}_logs")
        summary_report.add_metric("logs_processed", n_logs, "logs")
        summary_report.add_query_analysis(query_report)
        summary_report.add_timing({
            'with_query_tracking': tp_query.elapsed,
            'with_memory_tracking': tp_mem.elapsed
        })
        summary_report.add_memory(mp.memory_mb, mp.peak_mb)

        summary_path = summary_report.save(reports_dir, format='text')
        print(f"  ✓ Saved summary report: {summary_path}")

        print("")

    # Print Summary
    print("=" * 80)
    print("PROFILING SUMMARY")
    print("=" * 80)
    print("")

    print(f"Test Configuration:")
    print(f"  Machine logs: {n_logs}")
    print(f"  Employees: {len(test_env['employees'])}")
    print(f"  Shifts: {len(test_env['shifts'])}")
    print(f"  Devices: {len(test_env['devices'])}")
    print("")

    print(f"Query Analysis:")
    print(f"  Total queries: {query_report['total_queries']}")
    print(f"  Queries per log: {query_report['total_queries'] / n_logs:.2f}")
    print(f"  SELECT: {query_report['by_type']['SELECT']}")
    print(f"  INSERT: {query_report['by_type']['INSERT']}")
    print(f"  UPDATE: {query_report['by_type']['UPDATE']}")
    print("")

    print(f"Timing:")
    print(f"  Execution time: {tp_query.elapsed:.4f}s")
    print(f"  Time per log: {tp_query.elapsed / n_logs:.6f}s")
    print("")

    print(f"Memory:")
    print(f"  Memory delta: {mp.memory_mb:.2f} MB")
    print(f"  Peak memory: {mp.peak_mb:.2f} MB")
    print(f"  Memory per log: {mp.memory_mb / n_logs:.6f} MB")
    print("")

    if query_report['n_plus_one_suspects']:
        print(f"N+1 Query Suspects ({len(query_report['n_plus_one_suspects'])} found):")
        for i, suspect in enumerate(query_report['n_plus_one_suspects'][:3], 1):
            print(f"  {i}. Executed {suspect['count']} times, {suspect['total_time']:.4f}s total")
            print(f"     Pattern: {suspect['pattern'][:80]}...")
        print("")

    # Clean up test data
    print("[CLEANUP] Removing test data...")
    cleanup_test_data()
    print("  ✓ Test data cleaned up")
    print("")

    print("=" * 80)
    print("PROFILING COMPLETE")
    print("=" * 80)

    return results


def _cleanup_created_checkins():
    """Helper to clean up created checkins between profiling runs"""
    frappe.db.sql("""
        DELETE FROM `tabMachine Log`
        WHERE device LIKE 'PERFTEST_DEVICE%'
    """)

    frappe.db.sql("""
        DELETE FROM `tabEmployee Checkin`
        WHERE employee LIKE 'PERFTEST_EMP%'
    """)

    frappe.db.commit()


def quick_profile(n_logs=100):
    """
    Quick profiling run without full reports

    Args:
        n_logs: Number of logs to test with (default: 100)

    Returns:
        dict: Basic performance metrics
    """
    print(f"Quick Profile: {n_logs} logs\n")

    # Setup
    test_env = setup_complete_test_environment(n_employees=20, n_shifts=5, n_devices=3)
    logs = create_test_machine_logs(n_logs, test_env['employees'], test_env['devices'])

    # Profile
    with QueryCounter() as qc:
        with TimingProfiler("create_employee_checkin") as tp:
            create_employee_checkin()

    query_report = qc.get_report()

    # Results
    print(f"\nResults:")
    print(f"  Time: {tp.elapsed:.4f}s")
    print(f"  Queries: {query_report['total_queries']}")
    print(f"  Queries/log: {query_report['total_queries'] / n_logs:.2f}")

    # Cleanup
    cleanup_test_data()

    return {
        'time': tp.elapsed,
        'queries': query_report['total_queries'],
        'queries_per_log': query_report['total_queries'] / n_logs
    }


def compare_profiles(baseline_logs=100, comparison_logs=1000):
    """
    Compare performance at different scales

    Args:
        baseline_logs: Number of logs for baseline
        comparison_logs: Number of logs for comparison

    Returns:
        dict: Comparison results
    """
    print("=" * 80)
    print(f"PROFILE COMPARISON: {baseline_logs} vs {comparison_logs} logs")
    print("=" * 80)
    print("")

    # Run baseline
    print(f"Running baseline ({baseline_logs} logs)...")
    baseline = quick_profile(baseline_logs)

    print(f"\nRunning comparison ({comparison_logs} logs)...")
    comparison = quick_profile(comparison_logs)

    # Calculate scaling
    scale_factor = comparison_logs / baseline_logs

    time_scaling = comparison['time'] / baseline['time']
    query_scaling = comparison['queries'] / baseline['queries']

    print(f"\n" + "=" * 80)
    print(f"COMPARISON RESULTS")
    print(f"=" * 80)
    print(f"\nScale Factor: {scale_factor:.1f}x more logs")
    print(f"\nTime Scaling:")
    print(f"  Baseline: {baseline['time']:.4f}s for {baseline_logs} logs")
    print(f"  Comparison: {comparison['time']:.4f}s for {comparison_logs} logs")
    print(f"  Scaling: {time_scaling:.2f}x (ideal: {scale_factor:.1f}x for O(n))")

    if time_scaling < scale_factor * 1.2:
        print(f"  ✓ Scaling is linear or better")
    else:
        print(f"  ⚠ Scaling is super-linear (potential bottleneck)")

    print(f"\nQuery Scaling:")
    print(f"  Baseline: {baseline['queries']} queries for {baseline_logs} logs")
    print(f"  Comparison: {comparison['queries']} queries for {comparison_logs} logs")
    print(f"  Scaling: {query_scaling:.2f}x (ideal: {scale_factor:.1f}x for O(n))")

    if query_scaling < scale_factor * 1.2:
        print(f"  ✓ Query count scales linearly or better")
    else:
        print(f"  ⚠ Query count scales super-linearly (N+1 problem likely)")

    print(f"\nQueries per Log:")
    print(f"  Baseline: {baseline['queries_per_log']:.2f}")
    print(f"  Comparison: {comparison['queries_per_log']:.2f}")

    if comparison['queries_per_log'] <= baseline['queries_per_log'] * 1.1:
        print(f"  ✓ Consistent query efficiency")
    else:
        print(f"  ⚠ Query efficiency degrading at scale")

    return {
        'baseline': baseline,
        'comparison': comparison,
        'scale_factor': scale_factor,
        'time_scaling': time_scaling,
        'query_scaling': query_scaling
    }


if __name__ == "__main__":
    # Run profiling with 1000 logs by default
    profile_create_employee_checkin(n_logs=1000)
