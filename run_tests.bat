@echo off
setlocal enabledelayedexpansion
title 🧪 Zoom Poll Automator - Test Suite

:: Define colors for better visibility
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

echo %GREEN%========================================================%RESET%
echo %GREEN%         🧪 ZOOM POLL AUTOMATOR - TEST SUITE            %RESET%
echo %GREEN%========================================================%RESET%
echo.

:: Check if venv exists
if not exist venv (
    echo %RED%Virtual environment not found. Please run setup.bat first.%RESET%
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate || (
    echo %RED%Failed to activate virtual environment.%RESET%
    pause
    exit /b 1
)



:: Create test reports directory
if not exist test-reports mkdir test-reports

:: Parse command line arguments
set TEST_TYPE=all
set VERBOSITY=-v
set GENERATE_METRICS=yes

if "%1"=="--quick" (
    set TEST_TYPE=quick
) else if "%1"=="--smoke" (
    set TEST_TYPE=smoke
) else if "%1"=="--integration" (
    set TEST_TYPE=integration
) else if "%1"=="--performance" (
    set TEST_TYPE=performance
) else if "%1"=="--security" (
    set TEST_TYPE=security
)

if "%2"=="-v" (
    set VERBOSITY=-v
) else if "%2"=="-vv" (
    set VERBOSITY=-vv
) else if "%2"=="-vvv" (
    set VERBOSITY=-vvv
)

if "%3"=="--no-metrics" (
    set GENERATE_METRICS=no
)

echo.
echo %GREEN%========================================================%RESET%
echo %GREEN%         🧪 RUNNING %TEST_TYPE% TESTS                    %RESET%
echo %GREEN%========================================================%RESET%
echo.

:: Run the appropriate tests based on user selection
if "%TEST_TYPE%"=="quick" (
    echo %YELLOW%Running quick tests only...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% -m "not slow" tests/
) else if "%TEST_TYPE%"=="smoke" (
    echo %YELLOW%Running smoke tests only...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% -m "smoke" tests/
) else if "%TEST_TYPE%"=="integration" (
    echo %YELLOW%Running integration tests only...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% -m "integration" tests/
) else if "%TEST_TYPE%"=="performance" (
    echo %YELLOW%Running performance tests only...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% -m "performance" tests/
) else if "%TEST_TYPE%"=="security" (
    echo %YELLOW%Running security tests only...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% tests/test_security.py
) else (
    echo %YELLOW%Running all tests...%RESET%
    pytest --cov=. --cov-report=html:test-reports/coverage --html=test-reports/report.html --self-contained-html %VERBOSITY% tests/
)

:: Get the exit code from pytest
set EXIT_CODE=%errorlevel%

:: Generate metrics reports if requested
if "%GENERATE_METRICS%"=="yes" (
    echo.
    echo %BLUE%Generating metric reports for charting...%RESET%
    python tests/test_metrics_analyzer.py --output-dir test-reports/chart-data
    echo %GREEN%✓ Metrics generated in test-reports/chart-data%RESET%
)

:: Display test summary
echo.
if %EXIT_CODE% EQU 0 (
    echo %GREEN%✅ All tests passed successfully!%RESET%
) else (
    echo %RED%❌ Some tests failed. Check the reports for details.%RESET%
)

echo.
echo %BLUE%Reports available at:%RESET%
echo %BLUE%- HTML Test Report: test-reports\report.html%RESET%
echo %BLUE%- Coverage Report: test-reports\coverage\index.html%RESET%
if "%GENERATE_METRICS%"=="yes" (
    echo %BLUE%- Chart Data: test-reports\chart-data\*.csv%RESET%
)
echo.

:: Deactivate virtual environment
call venv\Scripts\deactivate

echo %YELLOW%Press any key to exit...%RESET%
pause
exit /b %EXIT_CODE% 