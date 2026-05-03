"""
Scan configuration display and user confirmation.
"""

from logger import header, info, warning
from config import get_config, get_chip_size, get_step_size
from scan import calculate_scan_parameters


def _display_scan_configuration(
    points_x: int, points_y: int, total_points: int,
    estimated_time_minutes: float, estimated_time_seconds: float
) -> None:
    """Display the scan configuration details."""
    cfg = get_config()
    chip_size = get_chip_size()
    step_size = get_step_size()

    header("\n" + ("=" * 50))
    header("Scan Configuration Preview")
    header(("=" * 50))
    info(f"Chip size:         {chip_size[0]:.1f} x {chip_size[1]:.1f} mm")
    info(f"Step size:         {step_size[0]:.1f} x {step_size[1]:.1f} mm")
    info(f"Grid dimensions:   {points_x} x {points_y} points")
    info(f"Total points:      {total_points}")
    info(f"Estimated time:    {estimated_time_minutes:.1f} minutes ({estimated_time_seconds:.0f} seconds)")
    info(f"Output root:       {cfg.get('output_root', 'Not set')}")
    info(f"OctoPrint URL:     {cfg.get('octoprint_url', 'Not set')}")
    info("")


def _get_scan_confirmation() -> bool:
    """Get user confirmation to proceed with the scan."""
    while True:
        confirm = input("Proceed with scan? (y/n): ").lower().strip()
        if confirm == 'y':
            return True
        elif confirm == 'n':
            warning("Scan cancelled. You can modify xyz-stage/configuration/scan.py and run again.")
            return False
        else:
            warning("Please enter 'y' to proceed or 'n' to cancel.")


def display_scan_preview() -> bool:
    """Show scan parameters and get user confirmation.

    Returns:
        True if confirmed, False if cancelled.
    """
    chip_size = get_chip_size()
    step_size = get_step_size()

    points_x, points_y, total_points = calculate_scan_parameters(chip_size, step_size)

    estimated_time_seconds = total_points * 2
    estimated_time_minutes = estimated_time_seconds / 60

    _display_scan_configuration(points_x, points_y, total_points,
                                estimated_time_minutes, estimated_time_seconds)
    return _get_scan_confirmation()
