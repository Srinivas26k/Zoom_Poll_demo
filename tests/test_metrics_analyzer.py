"""
Utility script to analyze test metrics and generate CSV reports for charting

This script reads the JSON test metrics and outputs:
1. summary_stats.csv - Overall test statistics
2. performance_metrics.csv - Performance metrics for each test type
3. memory_usage.csv - Memory usage throughout test execution
"""
import os
import json
import csv
import argparse
from pathlib import Path
import datetime
import statistics

def load_metrics(metrics_file=None):
    """Load test metrics from file"""
    if metrics_file is None:
        metrics_file = "test-reports/latest_metrics.json"
    
    with open(metrics_file, 'r') as f:
        return json.load(f)

def generate_summary_stats(metrics, output_dir):
    """Generate summary statistics CSV"""
    summary = metrics["summary"]
    system_info = metrics["system_info"]
    
    # Create summary stats file
    output_file = Path(output_dir) / "summary_stats.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers
        writer.writerow(['Metric', 'Value'])
        
        # Write system info
        writer.writerow(['Timestamp', metrics["timestamp"]])
        writer.writerow(['Platform', system_info["platform"]])
        writer.writerow(['Python Version', system_info["python_version"]])
        writer.writerow(['CPU Count', system_info["cpu_count"]])
        writer.writerow(['Total Memory (MB)', f"{system_info['memory_total_mb']:.2f}"])
        
        # Write test summary
        writer.writerow(['Total Tests', summary["total"]])
        writer.writerow(['Passed Tests', summary["passed"]])
        writer.writerow(['Failed Tests', summary["failed"]])
        writer.writerow(['Skipped Tests', summary["skipped"]])
        writer.writerow(['Error Tests', summary["error"]])
        writer.writerow(['Expected Failures', summary["xfailed"]])
        writer.writerow(['Unexpected Passes', summary["xpassed"]])
        writer.writerow(['Total Duration (s)', f"{summary['duration']:.2f}"])
        
        # Calculate pass rate
        if summary["total"] > 0:
            pass_rate = (summary["passed"] / summary["total"]) * 100
            writer.writerow(['Pass Rate (%)', f"{pass_rate:.2f}"])
    
    return output_file

def generate_performance_metrics(metrics, output_dir):
    """Generate performance metrics CSV for each test type"""
    execution_times = metrics["performance"]["execution_times"]
    
    # Create performance metrics file
    output_file = Path(output_dir) / "performance_metrics.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers
        writer.writerow(['Test Type', 'Test Count', 'Min Duration (s)', 'Max Duration (s)', 
                         'Avg Duration (s)', 'Median Duration (s)', 'Total Duration (s)'])
        
        # Process each test type
        for test_type, tests in execution_times.items():
            durations = [test["duration"] for test in tests]
            
            if durations:
                min_duration = min(durations)
                max_duration = max(durations)
                avg_duration = sum(durations) / len(durations)
                median_duration = statistics.median(durations)
                total_duration = sum(durations)
                
                writer.writerow([
                    test_type, 
                    len(tests),
                    f"{min_duration:.4f}",
                    f"{max_duration:.4f}",
                    f"{avg_duration:.4f}",
                    f"{median_duration:.4f}",
                    f"{total_duration:.4f}"
                ])
    
    return output_file

def generate_memory_usage(metrics, output_dir):
    """Generate memory usage CSV for charting"""
    memory_data = metrics["performance"]["memory_usage"]
    
    # Create memory usage file
    output_file = Path(output_dir) / "memory_usage.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers
        writer.writerow(['Test', 'Memory (MB)', 'Timestamp'])
        
        # Write memory usage data
        for entry in memory_data:
            writer.writerow([
                entry["test"],
                f"{entry['memory_mb']:.2f}",
                entry["timestamp"]
            ])
    
    return output_file

def generate_test_details(metrics, output_dir):
    """Generate detailed test results CSV"""
    tests = metrics["tests"]
    
    # Create test details file
    output_file = Path(output_dir) / "test_details.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers
        writer.writerow(['Module', 'Test Name', 'Outcome', 'Duration (s)', 'Memory (MB)', 'Test Type'])
        
        # Write test details
        for test in tests:
            # Determine test type from markers
            test_type = "unknown"
            for marker in test["markers"]:
                if marker in ["integration", "performance", "security", "smoke"]:
                    test_type = marker
                    break
            
            writer.writerow([
                test["module"],
                test["name"],
                test["outcome"],
                f"{test['duration']:.4f}",
                f"{test['memory_mb']:.2f}",
                test_type
            ])
    
    return output_file

def analyze_metrics(metrics_file=None, output_dir="test-reports"):
    """Analyze test metrics and generate CSV reports"""
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metrics
    metrics = load_metrics(metrics_file)
    
    # Generate reports
    summary_file = generate_summary_stats(metrics, output_dir)
    performance_file = generate_performance_metrics(metrics, output_dir)
    memory_file = generate_memory_usage(metrics, output_dir)
    details_file = generate_test_details(metrics, output_dir)
    
    print(f"Generated summary statistics: {summary_file}")
    print(f"Generated performance metrics: {performance_file}")
    print(f"Generated memory usage data: {memory_file}")
    print(f"Generated test details: {details_file}")
    
    return {
        "summary": summary_file,
        "performance": performance_file,
        "memory": memory_file,
        "details": details_file
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze test metrics and generate CSV reports")
    parser.add_argument("--metrics-file", help="Path to metrics JSON file (default: test-reports/latest_metrics.json)")
    parser.add_argument("--output-dir", default="test-reports", help="Output directory for CSV reports")
    
    args = parser.parse_args()
    analyze_metrics(args.metrics_file, args.output_dir) 