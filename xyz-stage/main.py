from colorama import init as init_colorama

from octoprint_communication import (
    apply_printer_settings,
    set_octoprint_config,
    set_axis_directions,
    set_motion_enabled,
)
from Configuration.measurement import MEASUREMENT_CONFIG
from config import (
    get_config,
    get_chip_size,
    load_config_from_file,
    set_chip_size,
)
from logger import info, warning
from scan import build_scan_context, perform_scan
from scan_overview import generate_scan_overview
from scan_preview import display_scan_preview
from setup import pick_chip_corners_and_size
from evaluation_phase import run_evaluation_phase


def main() -> None:
    """Run the scanner workflow."""
    init_colorama()
    load_config_from_file()
    cfg = get_config()
    measurement_runtime = MEASUREMENT_CONFIG.runtime
    motion_enabled = bool(cfg.get("enable_motion", True))
    pico_enabled = bool(measurement_runtime.enable_picoscope)
    cw_enabled = bool(measurement_runtime.enable_chipwhisperer)

    info(
        "Mode: "
        f"motion={'on' if motion_enabled else 'off'}, "
        f"picoscope={'on' if pico_enabled else 'off'}, "
        f"chipwhisperer={'on' if cw_enabled else 'off'}"
    )

    if not motion_enabled:
        warning("Dry-run active: motion is disabled (MACHINE_ENABLE_MOTION=False).")
    if not pico_enabled:
        warning("Dry-run active: PicoScope communication is disabled.")
    if not cw_enabled:
        warning("Dry-run active: ChipWhisperer communication is disabled.")

    chip_size = get_chip_size()
    if chip_size[0] <= 0.0 or chip_size[1] <= 0.0:
        warning("Chip size is not set. Starting interactive chip size picking...")
        width, height = pick_chip_corners_and_size()
        set_chip_size((width, height))

    if "octoprint_url" in cfg:
        set_octoprint_config(
            octoprint_url=cfg.get("octoprint_url"),
            api_key_env_var=cfg.get("api_key_env"),
        )

    if "axis_directions" in cfg:
        set_axis_directions(cfg.get("axis_directions"))
    set_motion_enabled(motion_enabled)

    apply_printer_settings(
        cfg.get("max_feedrate"),
        cfg.get("steps_per_mm"),
        cfg.get("acceleration"),
        cfg.get("hop_height"),
    )

    if not display_scan_preview():
        return

    scan_ctx = build_scan_context()
    results = perform_scan(scan_ctx)
    generate_scan_overview(scan_ctx)

    run_evaluation_phase(results)


if __name__ == "__main__":
    main()
