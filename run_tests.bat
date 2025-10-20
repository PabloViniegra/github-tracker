@echo off
REM GitHub Activity Tracker API - Test Runner Script (Windows)
REM
REM This script provides convenient commands for running different test suites

setlocal enabledelayedexpansion

echo GitHub Activity Tracker API - Test Runner
echo ==========================================
echo.

set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

if "%TEST_TYPE%"=="all" goto run_all
if "%TEST_TYPE%"=="unit" goto run_unit
if "%TEST_TYPE%"=="integration" goto run_integration
if "%TEST_TYPE%"=="security" goto run_security
if "%TEST_TYPE%"=="services" goto run_services
if "%TEST_TYPE%"=="routes" goto run_routes
if "%TEST_TYPE%"=="coverage" goto run_coverage
if "%TEST_TYPE%"=="fast" goto run_fast
if "%TEST_TYPE%"=="failed" goto run_failed
if "%TEST_TYPE%"=="debug" goto run_debug
goto show_usage

:run_all
echo Running All Tests
echo ----------------------------------------
python -m pytest tests/ -v
goto end

:run_unit
echo Running Unit Tests
echo ----------------------------------------
python -m pytest tests/unit/ -v
goto end

:run_integration
echo Running Integration Tests
echo ----------------------------------------
python -m pytest tests/integration/ -v
goto end

:run_security
echo Running Security Tests
echo ----------------------------------------
python -m pytest -m security -v
goto end

:run_services
echo Running Service Tests
echo ----------------------------------------
python -m pytest -m services -v
goto end

:run_routes
echo Running Route Tests
echo ----------------------------------------
python -m pytest -m routes -v
goto end

:run_coverage
echo Running Tests with Coverage
echo ----------------------------------------
python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
echo.
echo Coverage report generated in htmlcov\index.html
goto end

:run_fast
echo Running Fast Tests Only
echo ----------------------------------------
python -m pytest -m "not slow" -v
goto end

:run_failed
echo Re-running Failed Tests
echo ----------------------------------------
python -m pytest --lf -v
goto end

:run_debug
echo Running Tests in Debug Mode
echo ----------------------------------------
python -m pytest tests/ -vv -s --tb=long
goto end

:show_usage
echo Unknown test type: %TEST_TYPE%
echo.
echo Usage: run_tests.bat [TYPE]
echo.
echo Available types:
echo   all         - Run all tests (default)
echo   unit        - Run unit tests only
echo   integration - Run integration tests only
echo   security    - Run security tests
echo   services    - Run service layer tests
echo   routes      - Run route handler tests
echo   coverage    - Run tests with coverage report
echo   fast        - Run fast tests only (skip slow tests)
echo   failed      - Re-run only failed tests
echo   debug       - Run tests with verbose debugging output
exit /b 1

:end
echo.
echo Tests completed!
