#!/bin/bash

# GitHub Activity Tracker API - Test Runner Script
#
# This script provides convenient commands for running different test suites

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}GitHub Activity Tracker API - Test Runner${NC}"
echo "=========================================="
echo ""

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}$1${NC}"
    echo "----------------------------------------"
}

# Parse command line arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    all)
        print_header "Running All Tests"
        python -m pytest tests/ -v
        ;;
    unit)
        print_header "Running Unit Tests"
        python -m pytest tests/unit/ -v
        ;;
    integration)
        print_header "Running Integration Tests"
        python -m pytest tests/integration/ -v
        ;;
    security)
        print_header "Running Security Tests"
        python -m pytest -m security -v
        ;;
    services)
        print_header "Running Service Tests"
        python -m pytest -m services -v
        ;;
    routes)
        print_header "Running Route Tests"
        python -m pytest -m routes -v
        ;;
    coverage)
        print_header "Running Tests with Coverage"
        python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    fast)
        print_header "Running Fast Tests Only"
        python -m pytest -m "not slow" -v
        ;;
    failed)
        print_header "Re-running Failed Tests"
        python -m pytest --lf -v
        ;;
    debug)
        print_header "Running Tests in Debug Mode"
        python -m pytest tests/ -vv -s --tb=long
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [TYPE]"
        echo ""
        echo "Available types:"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  security    - Run security tests"
        echo "  services    - Run service layer tests"
        echo "  routes      - Run route handler tests"
        echo "  coverage    - Run tests with coverage report"
        echo "  fast        - Run fast tests only (skip slow tests)"
        echo "  failed      - Re-run only failed tests"
        echo "  debug       - Run tests with verbose debugging output"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Tests completed!${NC}"
