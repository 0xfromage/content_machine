#!/usr/bin/env python3
"""
Script to run tests and verify that all fixes are working.
"""
import os
import sys
import subprocess
import argparse

def setup_environment():
    """Set up the environment for testing."""
    print("Setting up test environment...")
    
    # Run the test setup script
    try:
        subprocess.run([sys.executable, "tests/setup_test_env.py"], check=True)
        print("Test environment set up successfully.")
    except subprocess.CalledProcessError:
        print("Failed to set up test environment!")
        return False
        
    return True

def run_tests(specific_tests=None, verbose=False):
    """
    Run the tests.
    
    Args:
        specific_tests: List of specific test modules to run.
        verbose: Whether to show verbose output.
        
    Returns:
        True if all tests pass, False otherwise.
    """
    print("\nRunning tests...")
    
    # Build the command
    cmd = [sys.executable, "-m", "unittest"]
    
    if verbose:
        cmd.append("-v")
    
    if specific_tests:
        cmd.extend(specific_tests)
    else:
        cmd.append("discover")
        cmd.append("tests")
    
    # Run the tests
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    
    # Return whether tests passed
    return result.returncode == 0

def run_specific_tests():
    """Run specific tests that are known to be fixed."""
    fixed_tests = [
        "tests.test_processor.TestTextProcessor.test_clean_text",
        "tests.test_processor.TestTextProcessor.test_extract_keywords", 
        "tests.test_processor.TestTextProcessor.test_generate_hashtags",
        "tests.test_publisher.TestBasePublisher.test_publish_success",
    ]
    
    return run_tests(fixed_tests, verbose=True)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run tests for the Content Machine project.")
    parser.add_argument("--specific", action="store_true", help="Run only specific fixed tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    args = parser.parse_args()
    
    # Set up environment
    if not setup_environment():
        return 1
    
    # Run tests
    if args.specific:
        success = run_specific_tests()
    else:
        success = run_tests(verbose=args.verbose)
    
    # Print result
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())