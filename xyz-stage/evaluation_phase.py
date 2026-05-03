"""Post-scan interactive evaluation commands."""

import subprocess
import sys
from pathlib import Path

from octoprint_communication import move_head_by, send_gcode_command
from side_channel_types import Position, ScanResults
from trace_heatmap import render_trace_metric_heatmap


def run_evaluation_phase(results: ScanResults) -> None:
    """Interactive post-scan inspection utilities (movement only)."""
    print("\nScan complete! Entering evaluation phase.")
    print("The stepper motors will remain enabled for inspection/revisit until you exit.")
    print("Type 'help' for available commands.\n")

    result_points = list(results.keys())
    point_indices = {i: pt for i, pt in enumerate(result_points)}
    plot_script = Path(__file__).resolve().parents[1] / "sca-helpers" / "plot.py"

    def show_points() -> None:
        print("Scanned points (index: (X_mm, Y_mm) | trace):")
        for idx, (x, y) in point_indices.items():
            point_res = results[(x, y)]
            trace_state = "yes" if point_res.trace_path else "no"
            print(f"  {idx}: ({x:.3f}, {y:.3f}) | trace={trace_state}")

    def launch_plot_for_point(point: Position) -> None:
        point_res = results.get(point)
        if point_res is None or not point_res.trace_path:
            print("No trace file available for this point.")
            return
        trace_path = Path(point_res.trace_path)
        if not trace_path.exists():
            print(f"Trace file not found: {trace_path}")
            return
        if not plot_script.exists():
            print(f"Plot script not found: {plot_script}")
            return
        try:
            subprocess.Popen([sys.executable, str(plot_script), str(trace_path)])
            print(f"Launched plot for point ({point[0]:.3f}, {point[1]:.3f})")
        except Exception as exc:
            print(f"Failed to launch plot: {type(exc).__name__}: {exc}")

    if result_points:
        eval_pos = list(result_points[-1])
        selected_scanned_point = result_points[-1]
    else:
        eval_pos = [0.0, 0.0]
        selected_scanned_point = None

    while True:
        user_input = input("\n[eval] Enter command ('help' for options): ").strip().lower()
        if user_input in ("exit", "quit"):
            print("Exiting evaluation phase. Disabling steppers (M18).")
            send_gcode_command("M18")
            break
        elif user_input == "help":
            print(
                "\nEvaluation phase commands:\n"
                "  list            - List all scanned points with index\n"
                "  goto N          - Move to the N-th scanned point [e.g. 'goto 3']\n"
                "  move X Y        - Move to absolute coordinates [e.g. 'move 3.5 7.2']\n"
                "  plot            - Visualize trace for current selected scanned point\n"
                "  plot N          - Visualize trace for scanned point index N\n"
                "  heatmap         - Visualize absolute-strength heatmap over scanned points\n"
                "  exit, quit      - Disable steppers and exit evaluation phase\n"
            )
        elif user_input == "list":
            show_points()
        elif user_input.startswith("goto"):
            try:
                idx = int(user_input.split()[1])
                x, y = point_indices[idx]
                print(f"Moving to scanned point {idx}: ({x:.3f}, {y:.3f})")
                dx, dy = x - eval_pos[0], y - eval_pos[1]
                move_head_by(dx, dy, 0, hop=True)
                eval_pos[0], eval_pos[1] = x, y
                selected_scanned_point = (x, y)
            except KeyboardInterrupt:
                print("Move interrupted. Current position may be between points.")
            except Exception:
                print("Invalid index for 'goto'. Try 'list' first and check the point number.")
        elif user_input.startswith("move"):
            try:
                _, x, y = user_input.split()
                x, y = float(x), float(y)
                print(f"Moving to ({x:.3f}, {y:.3f})")
                dx, dy = x - eval_pos[0], y - eval_pos[1]
                move_head_by(dx, dy, 0, hop=True)
                eval_pos[0], eval_pos[1] = x, y
                selected_scanned_point = None
            except KeyboardInterrupt:
                print("Move interrupted. Current position may be between points.")
            except Exception:
                print("Invalid coordinates for 'move'. Usage: move X Y")
        elif user_input == "plot":
            if selected_scanned_point is None:
                print("No scanned point selected. Use 'goto N' first, or run 'plot N'.")
            else:
                launch_plot_for_point(selected_scanned_point)
        elif user_input.startswith("plot "):
            try:
                idx = int(user_input.split()[1])
                point = point_indices[idx]
                launch_plot_for_point(point)
            except Exception:
                print("Invalid index for 'plot'. Usage: plot N")
        elif user_input == "heatmap":
            try:
                render_trace_metric_heatmap(results)
                print("Launched heatmap using absolute-strength trace metric.")
            except Exception as exc:
                print(f"Failed to render heatmap: {type(exc).__name__}: {exc}")
        else:
            print("Unknown command. Type 'help' for options.")
