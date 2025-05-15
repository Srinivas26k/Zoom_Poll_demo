"""
Test logger module for recording detailed metrics during test execution
Outputs results in machine-readable formats for visualization
"""
import os
import json
import time
import datetime
import platform
import psutil
import pytest
import logging
from pathlib import Path

# Create a dedicated logger for test metrics
metrics_logger = logging.getLogger("test_metrics")
metrics_logger.setLevel(logging.INFO)

# Global variables to track test metrics
TEST_METRICS = {
    "timestamp": datetime.datetime.now().isoformat(),
    "system_info": {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
    },
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "error": 0,
        "xfailed": 0,
        "xpassed": 0,
        "duration": 0.0,
    },
    "performance": {
        "memory_usage": [],
        "execution_times": {}
    }
}

def setup_metrics_logging():
    """Set up the metrics logging to file"""
    # Create logs directory if it doesn't exist
    logs_dir = Path("test-reports/metrics")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a timestamped log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"test_metrics_{timestamp}.json"
    
    # Create a file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Set formatter
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    metrics_logger.addHandler(file_handler)
    
    return log_file

def record_test_result(item, call, duration):
    """Record a test result with detailed metrics"""
    global TEST_METRICS
    
    # Get test details
    test_name = item.name
    module_name = item.module.__name__
    
    # Record memory usage
    memory_info = psutil.Process(os.getpid()).memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)
    
    # Determine test outcome
    outcome = "unknown"
    if hasattr(call, "excinfo"):
        if call.excinfo is None:
            outcome = "passed"
        elif call.excinfo.errisinstance(pytest.skip.Exception):
            outcome = "skipped"
        elif call.excinfo.errisinstance(pytest.xfail.Exception):
            outcome = "xfailed"
        else:
            outcome = "failed"
    
    # Get test markers
    markers = [marker.name for marker in item.iter_markers()]
    
    # Record test info
    test_info = {
        "name": test_name,
        "module": module_name,
        "outcome": outcome,
        "duration": duration,
        "markers": markers,
        "memory_mb": memory_mb,
    }
    
    # Add to metrics
    TEST_METRICS["tests"].append(test_info)
    
    # Update summary counters
    TEST_METRICS["summary"]["total"] += 1
    if outcome in TEST_METRICS["summary"]:
        TEST_METRICS["summary"][outcome] += 1
    
    # Update performance metrics
    TEST_METRICS["performance"]["memory_usage"].append({
        "test": f"{module_name}.{test_name}",
        "memory_mb": memory_mb,
        "timestamp": time.time()
    })
    
    # Record execution time for this test type
    test_type = "unknown"
    for marker in markers:
        if marker in ["integration", "performance", "security", "smoke"]:
            test_type = marker
            break
    
    if test_type != "unknown":
        if test_type not in TEST_METRICS["performance"]["execution_times"]:
            TEST_METRICS["performance"]["execution_times"][test_type] = []
        
        TEST_METRICS["performance"]["execution_times"][test_type].append({
            "test": f"{module_name}.{test_name}",
            "duration": duration
        })

def save_metrics():
    """Save the collected metrics to file"""
    # Update final summary info
    TEST_METRICS["summary"]["duration"] = sum(test["duration"] for test in TEST_METRICS["tests"])
    
    # Add timestamp for completion
    TEST_METRICS["completed_at"] = datetime.datetime.now().isoformat()
    
    # Log the metrics as JSON
    metrics_logger.info(json.dumps(TEST_METRICS, indent=2))
    
    # Also save to a standardized location for easy access
    with open("test-reports/latest_metrics.json", "w") as f:
        json.dump(TEST_METRICS, f, indent=2)

@pytest.fixture(scope="session", autouse=True)
def setup_metrics(request):
    """Pytest fixture to set up metrics logging at the start of the test session"""
    # Setup metrics logging
    log_file = setup_metrics_logging()
    
    # Record session start
    start_time = time.time()
    
    yield
    
    # Calculate total duration
    total_duration = time.time() - start_time
    TEST_METRICS["total_duration"] = total_duration
    
    # Save metrics at the end of the session
    save_metrics()
    
    # Print summary info
    print(f"\nTest Metrics saved to: {log_file}")
    print(f"Total tests: {TEST_METRICS['summary']['total']}")
    print(f"Passed: {TEST_METRICS['summary']['passed']}")
    print(f"Failed: {TEST_METRICS['summary']['failed']}")
    print(f"Duration: {total_duration:.2f} seconds")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Pytest hook to intercept test results and record metrics"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call":  # Only record the call phase (not setup/teardown)
        record_test_result(item, call, report.duration)

def get_test_metrics():
    """Get the current test metrics"""
    return TEST_METRICS 