from octoprint_communication import move_head_by
from logger import header, info, warning, error, success
from typing import Dict, Optional

from side_channel_types import ChipSize, CornerHeights, Position


def _display_corner_calibration_intro(chip_size: ChipSize) -> None:
    """Display the introduction for corner height calibration."""
    header("\n" + "=" * 60)
    header("Corner Height Calibration for Out-of-Level Chips")
    header("=" * 60)

    info("\nThis optional calibration allows the probe to work with chips that are not perfectly level.")
    info("You'll set the probe height at each of the four corners of the scan area.")
    info("During scanning, the system will use linear interpolation to adjust the probe height.")
    info(f"Scan area: {chip_size[0]:.1f} x {chip_size[1]:.1f} mm")
    info("Corner order (user point of view): top-left → top-right → bottom-right → bottom-left")


def _ask_user_proceed_with_calibration() -> bool:
    """Ask user if they want to proceed with corner calibration."""
    while True:
        usr_in = input("\nProceed with corner height calibration? (y/n/s to skip): ").lower().strip()
        if usr_in == 'y':
            return True
        elif usr_in == 'n' or usr_in == 's':
            warning("Corner height calibration skipped. Using flat surface assumption.")
            return False
        else:
            warning("Please enter 'y' to proceed, 'n' to cancel, or 's' to skip.")


def _display_corner_calibration_instructions() -> None:
    """Display the instructions for corner calibration."""
    header("\nCorner Height Calibration Instructions:")
    info("• Move to each corner and adjust the probe height to just touch the chip surface")
    info("• For safety, the probe will start 5.0mm above the highest recorded corner before each corner probe")
    info("• Use the controls to raise/lower the probe:")
    info("  w/s - ±0.1mm (small adjustments)")
    info("  W/S - ±1.0mm (medium adjustments)")
    info("  f/v - ±5.0mm (large adjustments)")
    info("  c - Confirm height at current corner")
    info("  q - Quit calibration")


def _move_to_corner(x: float, y: float, current_pos: Position) -> Position:
    """Move the probe to the specified corner position."""
    delta_x = x - current_pos[0]
    delta_y = y - current_pos[1]

    if delta_x != 0 or delta_y != 0:
        # Safe-Z is handled explicitly in calibration logic.
        move_head_by(delta_x, delta_y, 0.0, hop=False)

    return (x, y)


def _display_corner_calibration_summary(
    corner_heights: CornerHeights,
    corners: Dict[str, Position],
) -> None:
    """Display the summary of corner calibration."""
    success("\n✓ Corner height calibration completed!")
    info("Height map:")
    for corner_name, (x, y) in corners.items():
        height = corner_heights[(x, y)]
        info(f"  {corner_name}: ({x:.1f}, {y:.1f}) -> {height:.2f}mm")


def _return_probe_to_origin(current_pos: Position, current_height: float) -> None:
    """Return the probe to the origin position."""
    header("\nReturning probe to scan origin (0,0)...")
    return_delta_x = 0.0 - current_pos[0]
    return_delta_y = 0.0 - current_pos[1]
    move_head_by(return_delta_x, return_delta_y, - current_height, hop=True)
    success("✓ Probe returned to origin.")


def calibrate_corner_heights(chip_size: ChipSize) -> Optional[CornerHeights]:
    """Interactive corner height calibration for non-flat chips.

    Args:
        chip_size: (width, height) in mm.

    Returns:
        Height map dict or None if skipped/cancelled.
    """
    _display_corner_calibration_intro(chip_size)

    if not _ask_user_proceed_with_calibration():
        return None

    corners = {
        "top-left": (0.0, 0.0),
        "top-right": (chip_size[0], 0.0),
        "bottom-right": (chip_size[0], chip_size[1]),
        "bottom-left": (0.0, chip_size[1])
    }

    corner_heights: CornerHeights = {}
    current_height = 0.0  # Start with current position as reference
    current_pos: Position = (0.0, 0.0)  # Start at top-left corner (origin)

    _display_corner_calibration_instructions()

    for corner_name, (x, y) in corners.items():
        header(f"\n--- Calibrating {corner_name} corner ({x:.1f}, {y:.1f}) ---")

        if corner_heights:
            max_recorded = max(corner_heights.values())
        else:
            max_recorded = current_height
        safe_start_height = max_recorded + 5.0

        if safe_start_height != current_height:
            dz = safe_start_height - current_height
            info(f"Raising to safe start height {safe_start_height:.2f}mm")
            move_head_by(0, 0, dz, hop=False)
            current_height = safe_start_height

        info(f"Moving to {corner_name} corner...")
        current_pos = _move_to_corner(x, y, current_pos)

        height = get_corner_height_adjustment(current_height, corner_name)
        if height is None:
            error("Calibration cancelled by user.")
            return None

        corner_heights[(x, y)] = height
        current_height = height
        success(f"✓ {corner_name} corner height set to {height:.2f}mm")

    _display_corner_calibration_summary(corner_heights, corners)
    _return_probe_to_origin(current_pos, current_height)

    return corner_heights


def get_corner_height_adjustment(initial_height: float, corner_name: str) -> Optional[float]:
    """Get height adjustment for a specific corner during calibration.

    Provides interactive height adjustment controls for calibrating probe height
    at a specific corner position. Uses the same control scheme as general
    height calibration but tailored for corner-specific feedback.

    Args:
        initial_height: Starting height offset in millimeters.
        corner_name: Descriptive name of the corner (e.g., "top-left").

    Returns:
        Calibrated height offset for this corner in millimeters, or None if cancelled.
    """
    height = initial_height
    info(f"Adjust probe height for {corner_name} corner.")
    info("Lower the probe until it just touches the chip surface, then confirm.")

    command_actions = {
        "w": (0.1, ""),
        "W": (1.0, " FAST"),
        "f": (5.0, " VERY FAST"),
        "s": (-0.1, ""),
        "S": (-1.0, " FAST"),
        "v": (-5.0, " VERY FAST"),
    }

    while True:
        try:
            usr_in = input(f"\n{corner_name} height: {height:.2f}mm | Cmd: ").strip()
            if usr_in == "c":
                success(f"Height confirmed at {height:.2f}mm for {corner_name}")
                break
            elif usr_in == "q":
                confirm = input(f"Quit calibration at {corner_name}? (y/n): ").lower().strip()
                if confirm == 'y':
                    return None
            elif usr_in in command_actions:
                delta, speed_desc = command_actions[usr_in]
                height += delta
                move_head_by(0, 0, delta, hop=False)
                direction = "raised" if delta > 0 else "lowered"
                info(f"Probe {direction} by {abs(delta):.1f}mm{speed_desc} to {height:.2f}mm")
            else:
                error("Invalid input. Use w/W/f/s/S/v/c/q.")
        except KeyboardInterrupt:
            warning(f"\nCalibration interrupted at {corner_name}")
            return None
    return height
