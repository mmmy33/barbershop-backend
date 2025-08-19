#!/usr/bin/env python3
"""
Test runner script for authentication tests.
Provides easy commands to run different types of tests.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run authentication tests")
    parser.add_argument(
        "--type", 
        choices=["all", "auth", "register", "login", "admin", "coverage"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.coverage or args.html:
        base_cmd.extend(["--cov=src"])
        if args.html:
            base_cmd.append("--cov-report=html")
        base_cmd.append("--cov-report=term-missing")
    
    # Test selection based on type
    if args.type == "all":
        cmd = base_cmd + ["tests/"]
        description = "All authentication tests"
    elif args.type == "auth":
        cmd = base_cmd + ["tests/test_auth.py"]
        description = "Authentication tests only"
    elif args.type == "register":
        cmd = base_cmd + ["tests/test_auth.py::TestRegister"]
        description = "Registration tests only"
    elif args.type == "login":
        cmd = base_cmd + ["tests/test_auth.py::TestLogin"]
        description = "Login tests only"
    elif args.type == "admin":
        cmd = base_cmd + ["tests/test_auth.py::TestAdminOnly"]
        description = "Admin tests only"
    elif args.type == "coverage":
        cmd = base_cmd + ["tests/", "--cov=src", "--cov-report=html", "--cov-report=term-missing"]
        description = "All tests with coverage report"
    
    # Run the tests
    success = run_command(cmd, description)
    
    if success and args.html:
        print("\n📊 HTML coverage report generated in htmlcov/index.html")
        print("Open it in your browser to view detailed coverage information.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
