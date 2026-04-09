"""
Profiling Utilities for Performance Testing

Provides reusable tools for measuring and analyzing performance:
- QueryCounter: Count and analyze database queries
- TimingProfiler: Measure execution time with statistics
- MemoryProfiler: Track memory usage
- PerformanceReport: Format and export results
"""

import time
import tracemalloc
import traceback
import statistics
import json
import frappe
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager


class QueryCounter:
    """
    Context manager to intercept and count database queries.

    Tracks:
    - Total query count
    - Query types (SELECT, INSERT, UPDATE, DELETE)
    - Query execution times
    - N+1 query patterns
    - Duplicate queries

    Usage:
        with QueryCounter() as qc:
            # Your code here
            frappe.db.get_value("Employee", "EMP-001", "name")

        report = qc.get_report()
        print(f"Total queries: {report['total_queries']}")
    """

    def __init__(self):
        self.queries = []
        self.original_sql = None
        self.start_time = None

    def __enter__(self):
        """Start tracking queries"""
        self.start_time = time.perf_counter()
        self.original_sql = frappe.db.sql

        def tracked_sql(query, *args, **kwargs):
            """Wrapper to track SQL queries"""
            query_start = time.perf_counter()
            result = self.original_sql(query, *args, **kwargs)
            query_time = time.perf_counter() - query_start

            self.queries.append({
                'query': query,
                'time': query_time,
                'timestamp': time.time(),
                'stack': traceback.extract_stack()[:-1]  # Exclude this frame
            })

            return result

        frappe.db.sql = tracked_sql
        return self

    def __exit__(self, *args):
        """Stop tracking queries"""
        frappe.db.sql = self.original_sql

    def get_report(self):
        """
        Generate comprehensive query analysis report

        Returns:
            dict: Analysis including counts, timings, and patterns
        """
        total_queries = len(self.queries)

        # Categorize queries by type
        select_count = sum(1 for q in self.queries if 'SELECT' in q['query'].upper())
        insert_count = sum(1 for q in self.queries if 'INSERT' in q['query'].upper())
        update_count = sum(1 for q in self.queries if 'UPDATE' in q['query'].upper())
        delete_count = sum(1 for q in self.queries if 'DELETE' in q['query'].upper())

        # Calculate timing statistics
        query_times = [q['time'] for q in self.queries]
        total_time = sum(query_times)

        timing_stats = {}
        if query_times:
            timing_stats = {
                'total_time': total_time,
                'mean': statistics.mean(query_times),
                'median': statistics.median(query_times),
                'min': min(query_times),
                'max': max(query_times)
            }

            if len(query_times) >= 2:
                timing_stats['stdev'] = statistics.stdev(query_times)

        # Detect N+1 patterns
        n_plus_one = self._detect_n_plus_one()

        # Find duplicate queries
        duplicates = self._find_duplicates()

        # Find slowest queries
        slowest = sorted(self.queries, key=lambda x: x['time'], reverse=True)[:5]
        slowest_queries = [
            {
                'query': q['query'][:200],  # Truncate long queries
                'time': q['time']
            }
            for q in slowest
        ]

        return {
            'total_queries': total_queries,
            'by_type': {
                'SELECT': select_count,
                'INSERT': insert_count,
                'UPDATE': update_count,
                'DELETE': delete_count
            },
            'timing': timing_stats,
            'n_plus_one_suspects': n_plus_one,
            'duplicate_count': len(duplicates),
            'duplicates': duplicates[:10],  # Show first 10
            'slowest_queries': slowest_queries
        }

    def _detect_n_plus_one(self):
        """
        Detect potential N+1 query patterns

        Looks for repeated similar queries that might indicate
        queries inside loops.

        Returns:
            list: Suspected N+1 query patterns
        """
        # Group queries by normalized pattern
        patterns = defaultdict(list)

        for q in self.queries:
            # Simple pattern extraction (remove specific values)
            pattern = self._normalize_query(q['query'])
            patterns[pattern].append(q)

        # Find patterns that repeat many times
        suspects = []
        for pattern, queries in patterns.items():
            if len(queries) > 5:  # Threshold for N+1 suspicion
                suspects.append({
                    'pattern': pattern[:200],
                    'count': len(queries),
                    'total_time': sum(q['time'] for q in queries),
                    'avg_time': sum(q['time'] for q in queries) / len(queries)
                })

        return sorted(suspects, key=lambda x: x['count'], reverse=True)

    def _normalize_query(self, query):
        """Normalize query for pattern matching"""
        import re
        # Replace numbers and strings with placeholders
        normalized = re.sub(r'\d+', 'N', query)
        normalized = re.sub(r"'[^']*'", 'STR', normalized)
        normalized = re.sub(r'"[^"]*"', 'STR', normalized)
        return normalized

    def _find_duplicates(self):
        """Find exact duplicate queries"""
        query_counts = defaultdict(int)

        for q in self.queries:
            query_counts[q['query']] += 1

        duplicates = [
            {'query': query[:200], 'count': count}
            for query, count in query_counts.items()
            if count > 1
        ]

        return sorted(duplicates, key=lambda x: x['count'], reverse=True)


class TimingProfiler:
    """
    Context manager for timing code execution

    Supports:
    - Basic timing
    - Statistical analysis (mean, median, percentiles)
    - Multiple run comparison

    Usage:
        with TimingProfiler("My Operation") as tp:
            # Your code here
            time.sleep(0.1)

        print(f"Took {tp.elapsed:.4f}s")
    """

    def __init__(self, label="Operation"):
        self.label = label
        self.start_time = None
        self.elapsed = None
        self.timings = []

    def __enter__(self):
        """Start timing"""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        """Stop timing"""
        self.elapsed = time.perf_counter() - self.start_time
        self.timings.append(self.elapsed)
        print(f"[TIMING] {self.label}: {self.elapsed:.4f}s")

    def get_stats(self):
        """Get statistical analysis of timings"""
        if not self.timings:
            return None

        return {
            'count': len(self.timings),
            'total': sum(self.timings),
            'mean': statistics.mean(self.timings),
            'median': statistics.median(self.timings),
            'min': min(self.timings),
            'max': max(self.timings),
            'stdev': statistics.stdev(self.timings) if len(self.timings) >= 2 else 0
        }


@contextmanager
def timing_context(label):
    """
    Simple context manager for timing with print output

    Usage:
        with timing_context("Database Query"):
            frappe.db.sql("SELECT * FROM tabEmployee")
    """
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"[TIMING] {label}: {elapsed:.4f}s")


class MemoryProfiler:
    """
    Context manager for tracking memory usage

    Uses tracemalloc to measure memory delta and peak usage

    Usage:
        with MemoryProfiler("My Operation") as mp:
            # Your code here
            big_list = [i for i in range(1000000)]

        print(f"Memory used: {mp.memory_mb:.2f} MB")
    """

    def __init__(self, label="Operation"):
        self.label = label
        self.start_snapshot = None
        self.memory_mb = None
        self.peak_mb = None

    def __enter__(self):
        """Start tracking memory"""
        tracemalloc.start()
        self.start_snapshot = tracemalloc.take_snapshot()
        return self

    def __exit__(self, *args):
        """Stop tracking memory"""
        current = tracemalloc.take_snapshot()
        stats = current.compare_to(self.start_snapshot, 'lineno')

        # Calculate total memory delta
        total_delta = sum(stat.size_diff for stat in stats)
        self.memory_mb = total_delta / 1024 / 1024

        # Get peak memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        self.peak_mb = peak_mem / 1024 / 1024

        tracemalloc.stop()

        print(f"[MEMORY] {self.label}: Delta={self.memory_mb:.2f} MB, Peak={self.peak_mb:.2f} MB")

    def get_top_allocations(self, n=10):
        """Get top N memory allocations"""
        if self.start_snapshot is None:
            return []

        current = tracemalloc.take_snapshot()
        stats = current.compare_to(self.start_snapshot, 'lineno')

        return [
            {
                'size_mb': stat.size_diff / 1024 / 1024,
                'count': stat.count_diff,
                'file': str(stat.traceback)
            }
            for stat in stats[:n]
        ]


class PerformanceReport:
    """
    Generate formatted performance reports

    Supports multiple output formats:
    - Text (human-readable)
    - JSON (machine-readable)
    - CSV (for spreadsheets)
    """

    def __init__(self, test_name):
        self.test_name = test_name
        self.timestamp = datetime.now()
        self.metrics = {}

    def add_metric(self, name, value, unit=""):
        """Add a metric to the report"""
        self.metrics[name] = {
            'value': value,
            'unit': unit
        }

    def add_query_analysis(self, query_report):
        """Add query analysis from QueryCounter"""
        self.metrics['queries'] = query_report

    def add_timing(self, timing_stats):
        """Add timing statistics from TimingProfiler"""
        self.metrics['timing'] = timing_stats

    def add_memory(self, memory_mb, peak_mb):
        """Add memory statistics from MemoryProfiler"""
        self.metrics['memory'] = {
            'delta_mb': memory_mb,
            'peak_mb': peak_mb
        }

    def to_text(self):
        """Generate human-readable text report"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Performance Report: {self.test_name}")
        lines.append(f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")

        for metric_name, metric_data in self.metrics.items():
            lines.append(f"{metric_name.upper()}:")

            if isinstance(metric_data, dict):
                for key, value in metric_data.items():
                    if isinstance(value, (int, float)):
                        lines.append(f"  {key}: {value:.4f}")
                    elif isinstance(value, dict):
                        lines.append(f"  {key}:")
                        for k, v in value.items():
                            lines.append(f"    {k}: {v}")
                    else:
                        lines.append(f"  {key}: {value}")
            else:
                unit = metric_data.get('unit', '')
                value = metric_data.get('value', metric_data)
                lines.append(f"  {value} {unit}")

            lines.append("")

        return "\n".join(lines)

    def to_json(self):
        """Generate JSON report"""
        return json.dumps({
            'test_name': self.test_name,
            'timestamp': self.timestamp.isoformat(),
            'metrics': self.metrics
        }, indent=2)

    def save(self, directory, format='text'):
        """Save report to file"""
        timestamp_str = self.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{self.test_name}_{timestamp_str}"

        if format == 'text':
            filepath = f"{directory}/{filename}.txt"
            with open(filepath, 'w') as f:
                f.write(self.to_text())
        elif format == 'json':
            filepath = f"{directory}/{filename}.json"
            with open(filepath, 'w') as f:
                f.write(self.to_json())

        return filepath


def calculate_percentiles(values, percentiles=[50, 95, 99]):
    """
    Calculate percentiles from a list of values

    Args:
        values: List of numeric values
        percentiles: List of percentile values to calculate (0-100)

    Returns:
        dict: Percentile values
    """
    if not values:
        return {}

    sorted_values = sorted(values)
    n = len(sorted_values)

    results = {}
    for p in percentiles:
        index = int((p / 100) * (n - 1))
        results[f'p{p}'] = sorted_values[index]

    return results


def compare_results(baseline, current, metric_name):
    """
    Compare two performance results

    Args:
        baseline: Baseline value
        current: Current value
        metric_name: Name of the metric being compared

    Returns:
        dict: Comparison analysis
    """
    if baseline == 0:
        percent_change = float('inf') if current > 0 else 0
    else:
        percent_change = ((current - baseline) / baseline) * 100

    absolute_change = current - baseline

    status = "improved" if percent_change < 0 else "regressed" if percent_change > 0 else "unchanged"

    return {
        'metric': metric_name,
        'baseline': baseline,
        'current': current,
        'absolute_change': absolute_change,
        'percent_change': percent_change,
        'status': status
    }
