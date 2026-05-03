"""
Pre-scan setup verification and user confirmation.
"""

from logger import info, warning, error, success


def pick_chip_corners_and_size() -> tuple[float, float]:
    """
    Interactively pick two corners for the chip and compute chip_size.

    Returns:
        (chip_width, chip_height) in mm, as chosen by the user.
    """
    from logger import info, warning, error, success
    from octoprint_communication import move_head_by

    x, y = 0.0, 0.0
    info("\nChip Dimension Setup (Interactive)")
    info("Step 1: Position the probe at the FIRST corner (origin) of the chip.")
    info("You may physically reposition the tool and press Enter when ready.")

    input("Press Enter when the head is above the first (origin) corner...")

    info("Origin corner established at (X=0.00mm, Y=0.00mm).")

    info("\nStep 2: Use nudge commands to move the probe to the diagonally opposite corner.")
    info("Controls: (move in mm)")
    info("  d = +X (right), a = -X (left)")
    info("  w = +Y (DOWN), s = -Y (UP)")
    info("  D = +10X, A = -10X, W = +10Y, S = -10Y")
    info("  c = confirm position at second corner")
    info("  q = quit setup")

    nudge = {
        "d": (-1.0, 0),
        "a": (1.0, 0),
        "w": (0, -1.0),
        "s": (0, 1.0),
        "D": (-10.0, 0),
        "A": (10.0, 0),
        "W": (0, -10.0),
        "S": (0, 10.0)
    }

    while True:
        info(f"\nCurrent probe position: X={x:.2f}mm, Y={y:.2f}mm")
        cmd = input("Command (move/nudge, c=confirm, q=quit): ").strip()
        if cmd in nudge:
            dx, dy = nudge[cmd]
            x += dx
            y += dy
            move_head_by(dx, dy, 0, hop=True)
            info(f"Moved to X={x:.2f}mm, Y={y:.2f}mm")
        elif cmd == "c":
            success(f"Corner confirmed at X={x:.2f}mm, Y={y:.2f}mm.")
            width, height = abs(x), abs(y)
            info(f"Chip dimensions set: width={width:.2f}mm, height={height:.2f}mm")
            if abs(x) > 1e-7 or abs(y) > 1e-7:
                info("Returning probe to origin (0, 0)...")
                move_head_by(-x, -y, 0, hop=True)
                info("Probe returned to (0,0).")
            return (width, height)
        elif cmd == "q":
            warning("Chip size picking cancelled.")
            raise KeyboardInterrupt("Chip dimension picking aborted by user.")
        else:
            warning("Unknown command. Use a/d/w/s/D/A/W/S to nudge, c=confirm, q=quit.")
