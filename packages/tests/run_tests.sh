#!/usr/bin/env bash
#
# run_tests.sh - Comprehensive test runner for namespace package tests
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh --fast       # Skip slow tests
#   ./run_tests.sh --coverage   # Generate coverage report
#   ./run_tests.sh --help       # Show help
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default options
FAST_MODE=false
COVERAGE=false
PARALLEL=false
VERBOSE=false
MARKERS=""
PYTEST_ARGS=""

# Help message
show_help() {
    cat << EOF
Netrun Namespace Package Test Runner

Usage: $0 [OPTIONS]

OPTIONS:
    --fast          Skip slow tests
    --coverage      Generate coverage reports
    --parallel      Run tests in parallel
    --verbose, -v   Verbose output
    --markers EXPR  Run only tests matching marker expression
    --help, -h      Show this help message

EXAMPLES:
    $0                              # Run all tests
    $0 --fast                       # Quick run (skip slow tests)
    $0 --coverage                   # Run with coverage
    $0 --parallel                   # Parallel execution
    $0 --markers namespace          # Only namespace tests
    $0 --markers "not integration"  # Exclude integration tests
    $0 --verbose --coverage         # Verbose with coverage

MARKERS:
    namespace           Namespace-specific tests
    integration         Integration tests (require multiple packages)
    backwards_compat    Backwards compatibility tests
    pep561             Type checking compliance tests
    slow               Slow tests (can be excluded with --fast)
    py310, py311, py312 Python version-specific tests

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            FAST_MODE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --markers)
            MARKERS="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Netrun Namespace Package Import Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Python Version:${NC} $PYTHON_VERSION"
echo ""

# Check if pytest is installed
if ! python3 -m pytest --version &> /dev/null; then
    echo -e "${RED}ERROR: pytest is not installed${NC}"
    echo -e "${YELLOW}Install with: pip install -r requirements-test.txt${NC}"
    exit 1
fi

# Build pytest command
PYTEST_CMD="python3 -m pytest test_namespace_imports.py"

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add marker filtering
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m \"$MARKERS\""
fi

# Add fast mode (exclude slow tests)
if [ "$FAST_MODE" = true ]; then
    echo -e "${YELLOW}Fast mode: Skipping slow tests${NC}"
    PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}Coverage enabled${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    echo -e "${YELLOW}Parallel execution enabled${NC}"
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add other useful flags
PYTEST_CMD="$PYTEST_CMD --tb=short --strict-markers"

echo -e "${GREEN}Running tests...${NC}"
echo -e "${BLUE}Command:${NC} $PYTEST_CMD"
echo ""

# Run tests
eval $PYTEST_CMD
TEST_EXIT_CODE=$?

echo ""

# Check test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"

    # Show coverage report location if generated
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${GREEN}Coverage reports generated:${NC}"
        echo -e "  - HTML: ${BLUE}htmlcov/index.html${NC}"
        echo -e "  - XML:  ${BLUE}coverage.xml${NC}"
        echo ""
        echo -e "Open HTML report: ${YELLOW}open htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}✗ Tests failed with exit code: $TEST_EXIT_CODE${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"

exit $TEST_EXIT_CODE
