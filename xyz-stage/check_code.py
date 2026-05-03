"""
Code quality checking script for the side-channel scanner.

Runs mypy type checking and pycodestyle style checking on the codebase.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*50}")
    print(f"Running {description}...")
    print('='*50)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {description}: {e}", file=sys.stderr)
        return False

def main() -> int:
    """Run all code quality checks."""
    project_root = Path(__file__).parent

    python_files = [
        "main.py",
        "config.py",
        "scan.py",
        "calibration.py",
        "setup.py",
        "scan_preview.py",
        "logger.py",
        "octoprint_communication.py",
        "sidechannel_payload.py",
    ]

    print("Side-Channel Scanner - Code Quality Checks")
    print("=" * 50)

    pycodestyle_cmd = f"pycodestyle {' '.join(python_files)}"
    style_ok = run_command(pycodestyle_cmd, "pycodestyle (PEP 8 style check)")

    mypy_cmd = f"mypy {' '.join(python_files)}"
    types_ok = run_command(mypy_cmd, "mypy (type checking)")

    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    print(f"Style check (pycodestyle): {'✓ PASS' if style_ok else '✗ FAIL'}")
    print(f"Type check (mypy): {'✓ PASS' if types_ok else '✗ FAIL'}")

    if style_ok and types_ok:
        print("\n🎉 All checks passed!")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
