"""
Centralized logging with color-coded console output.
"""

from colorama import Fore, Style


def header(msg: str) -> None:
    """Print a header message in cyan."""
    print(Fore.CYAN + msg + Style.RESET_ALL)


def success(msg: str) -> None:
    """Print a success message in green."""
    print(Fore.GREEN + msg + Style.RESET_ALL)


def error(msg: str) -> None:
    """Print an error message in red."""
    print(Fore.RED + msg + Style.RESET_ALL)


def warning(msg: str) -> None:
    """Print a warning message in yellow."""
    print(Fore.YELLOW + msg + Style.RESET_ALL)


def info(msg: str) -> None:
    """Print an info message without color."""
    print(msg)
