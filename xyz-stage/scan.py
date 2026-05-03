"""Scan loop orchestration."""

from dataclasses import dataclass, field
from datetime import datetime
import os
from typing import List, Optional, Tuple

from config import get_chip_size, get_output_root, get_step_size
from octoprint_communication import move_head_by
from sidechannel_payload import PayloadContext, cleanup_payload, run_payload, setup_payload
from logger import error, header, info, success, warning
from calibration import calibrate_corner_heights
from side_channel_types import ChipSize, CornerHeights, Position, ScanPointResult, ScanResults, StepSize


@dataclass
class ScanContext:
    chip_size: ChipSize
    step_size: StepSize
    output_root: str
    positions: List[Position]
    total_points: int
    corner_heights: Optional[CornerHeights] = None
    current_pos: Position = (0.0, 0.0)
    current_z: float = 0.0
    results: ScanResults = field(default_factory=dict)
    successful_measurements: int = 0
    interrupted: bool = False
    payload_output_folder: Optional[str] = None
    captured_points_log: List[str] = field(default_factory=list)


def calculate_scan_parameters(chip_size: ChipSize, step_size: StepSize) -> Tuple[int, int, int]:
    """Return (points_x, points_y, total_points)."""
    x_positions = build_axis_positions(chip_size[0], step_size[0])
    y_positions = build_axis_positions(chip_size[1], step_size[1])
    points_x = len(x_positions)
    points_y = len(y_positions)
    total_points = points_x * points_y
    return points_x, points_y, total_points


def build_axis_positions(size: float, step: float) -> List[float]:
    """Build monotonic scan coordinates from 0 to size (inclusive) without overshoot."""
    if size < 0:
        raise ValueError("Chip axis size must be >= 0.")
    if step <= 0:
        raise ValueError("Step size must be > 0.")

    eps = 1e-9
    if size <= eps:
        return [0.0]

    positions: List[float] = [0.0]
    cursor = 0.0
    while cursor + step < size - eps:
        cursor += step
        # Hard clamp avoids fencepost overshoot from floating-point drift.
        positions.append(min(cursor, size))

    if abs(positions[-1] - size) > eps:
        positions.append(size)

    return positions


def generate_scan_positions(chip_size: ChipSize, step_size: StepSize) -> List[Position]:
    x_positions = build_axis_positions(chip_size[0], step_size[0])
    y_positions = build_axis_positions(chip_size[1], step_size[1])

    positions: List[Position] = []
    for pos_x in x_positions:
        for pos_y in y_positions:
            positions.append((pos_x, pos_y))
    return positions


def build_scan_context() -> ScanContext:
    chip_size = get_chip_size()
    step_size = get_step_size()
    output_root = get_output_root()
    _, _, total_points = calculate_scan_parameters(chip_size, step_size)
    positions = generate_scan_positions(chip_size, step_size)
    return ScanContext(
        chip_size=chip_size,
        step_size=step_size,
        output_root=output_root,
        positions=positions,
        total_points=total_points,
    )


def interpolate_height(
    x: float,
    y: float,
    corner_heights: Optional[CornerHeights],
    chip_size: ChipSize,
) -> float:
    """Return interpolated Z offset at (x_mm, y_mm)."""
    if corner_heights is None:
        return 0.0

    width, height = chip_size

    h00 = corner_heights.get((0.0, 0.0), 0.0)
    h10 = corner_heights.get((width, 0.0), 0.0)
    h11 = corner_heights.get((width, height), 0.0)
    h01 = corner_heights.get((0.0, height), 0.0)


    x_norm = x / width if width > 0 else 0
    y_norm = y / height if height > 0 else 0

    x_norm = max(0.0, min(1.0, x_norm))
    y_norm = max(0.0, min(1.0, y_norm))

    interpolated_height = (
        h00 * (1 - x_norm) * (1 - y_norm)
        + h10 * x_norm * (1 - y_norm)
        + h11 * x_norm * y_norm
        + h01 * (1 - x_norm) * y_norm
    )

    return interpolated_height


def perform_measurement_at_position(
    ctx: ScanContext,
    pos: Position,
    point_index: int,
    payload_ctx: PayloadContext,
) -> Tuple[Position, ScanPointResult, float]:
    """Move to pos, invoke payload, return (pos, ok, z)."""
    delta_x = pos[0] - ctx.current_pos[0]
    delta_y = pos[1] - ctx.current_pos[1]
    target_z = interpolate_height(pos[0], pos[1], ctx.corner_heights, ctx.chip_size)
    delta_z = target_z - ctx.current_z

    move_head_by(delta_x, delta_y, delta_z)
    new_pos = pos
    new_z = target_z

    try:
        trace_path = run_payload(payload_ctx, point_index=point_index, coords=new_pos)
    except Exception as e:
        warning(f"Payload error at pos {pos}: {type(e).__name__}: {e}")
        return new_pos, ScanPointResult(ok=False, trace_path=None), new_z

    return new_pos, ScanPointResult(ok=True, trace_path=trace_path), new_z


def print_scan_progress(i: int, total_points: int, pos: Position,
                         target_z: float, successful_measurements: int) -> None:
    """Print progress line."""
    success_rate = (successful_measurements / (i + 1)) * 100
    header(f"Scanning: {i + 1}/{total_points} points | "
           f"Pos: ({pos[0]:.1f},{pos[1]:.1f})mm | "
           f"Height: {target_z:.2f}mm | Success: {success_rate:.1f}%")


def run_scan_loop(
    ctx: ScanContext,
    payload_ctx: PayloadContext,
) -> None:
    """Iterate positions, mutating context results and movement state."""
    for i, pos in enumerate(ctx.positions):
        completed_points = len(ctx.results)
        info(
            f"Completed {completed_points}/{ctx.total_points} points. "
        )
        try:
            new_pos, point_result, new_z = perform_measurement_at_position(ctx, pos, i, payload_ctx)
        except KeyboardInterrupt:
            warning("\nScan interrupted by user. Keeping measurements collected so far.")
            ctx.interrupted = True
            break
        ctx.current_pos = new_pos
        ctx.current_z = new_z
        ctx.results[pos] = point_result

        if point_result.ok:
            ctx.successful_measurements += 1
            ctx.captured_points_log.append(
                f"{i}: x={new_pos[0]:.3f} mm, y={new_pos[1]:.3f} mm, z={new_z:.3f} mm"
            )
        else:
            warning(
                "Trace capture failed. Stopping scan early and moving to exploration/evaluation phase."
            )
            ctx.interrupted = True
            break

        if i % 10 == 0 or i == len(ctx.positions) - 1:
            print_scan_progress(
                i,
                ctx.total_points,
                pos,
                ctx.current_z,
                ctx.successful_measurements,
            )


def perform_scan(scan_ctx: ScanContext) -> ScanResults:
    """Run the scan. Returns (x_mm, y_mm) -> ok. Payload stores its own data."""
    scan_ctx.corner_heights = calibrate_corner_heights(scan_ctx.chip_size)
    if scan_ctx.corner_heights is None:
        warning("Proceeding with flat surface assumption.")
    else:
        success("Using interpolated height correction for out-of-level chip.")

    header(f"Starting scan of {scan_ctx.total_points} points... "
           f"Press Ctrl+C to stop at any time.")
    info(
        f"Chip size: {scan_ctx.chip_size[0]:.1f} x {scan_ctx.chip_size[1]:.1f} mm, "
        f"Step size: {scan_ctx.step_size[0]:.1f} x {scan_ctx.step_size[1]:.1f} mm"
    )

    info("Initializing payload (setup_payload)...")
    payload_ctx = setup_payload(output_root=scan_ctx.output_root)
    scan_ctx.payload_output_folder = payload_ctx.output_folder
    write_scan_settings_file(scan_ctx)

    try:
        run_scan_loop(scan_ctx, payload_ctx)
    finally:
        cleanup_payload(payload_ctx)

    if scan_ctx.interrupted:
        warning("Scan ended early via Ctrl+C; visualization/evaluation will use partial results.")

    print_scan_summary(
        scan_ctx.results,
        scan_ctx.successful_measurements,
        scan_ctx.chip_size,
        scan_ctx.step_size,
    )
    print_captured_points_log(scan_ctx)
    return scan_ctx.results


def print_scan_summary(
    results: ScanResults,
    successful_measurements: int,
    chip_size: ChipSize,
    step_size: StepSize,
) -> None:
    """Print summary statistics."""
    if results:
        success_rate = (successful_measurements / len(results)) * 100 if results else 0
        success(f"\nScan completed!")
        info(f"  Total positions: {len(results)}")
        info(f"  Successful measurements: {successful_measurements}")
        info(f"  Success rate: {success_rate:.1f}%")
        info(f"  Chip size: {chip_size[0]:.1f} x {chip_size[1]:.1f} mm")
        info(f"  Step size: {step_size[0]:.1f} x {step_size[1]:.1f} mm")
    else:
        error("\nScan terminated without saving results.")


def write_scan_settings_file(scan_ctx: ScanContext) -> None:
    if not scan_ctx.payload_output_folder:
        return

    settings_path = os.path.join(scan_ctx.payload_output_folder, "scan_settings.txt")
    with open(settings_path, "w", encoding="utf-8") as fh:
        fh.write(f"Scan started: {datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"Output folder: {scan_ctx.payload_output_folder}\n")
        fh.write(f"Chip size (mm): {scan_ctx.chip_size[0]:.3f} x {scan_ctx.chip_size[1]:.3f}\n")
        fh.write(f"Step size (mm): {scan_ctx.step_size[0]:.3f} x {scan_ctx.step_size[1]:.3f}\n")
        fh.write(f"Total planned points: {scan_ctx.total_points}\n")
        if scan_ctx.corner_heights is None:
            fh.write("Corner heights: flat surface assumption (all zero)\n")
        else:
            fh.write("Corner heights (mm):\n")
            for corner_pos in sorted(scan_ctx.corner_heights):
                corner_h = scan_ctx.corner_heights[corner_pos]
                fh.write(
                    f"  ({corner_pos[0]:.3f}, {corner_pos[1]:.3f}) -> {corner_h:.3f}\n"
                )
        fh.write("TRS naming: point index from 0 to n (e.g., 0.trs, 1.trs, ...)\n")

    info(f"Saved scan settings to: {settings_path}")


def print_captured_points_log(scan_ctx: ScanContext) -> None:
    if not scan_ctx.captured_points_log:
        warning("No captured points to log.")
        return

    header("Captured points (index -> x, y, z):")
    for line in scan_ctx.captured_points_log:
        info(f"  {line}")
