# XYZ Stage Operator Guide (Post-Setup)

This guide is for routine operation after environment and hardware setup are already complete.

## 1) Pre-run checklist

Before each run:
- Confirm the correct Python venv is active.
- Confirm `API_KEY_OCTO` is set in the current shell (if motion is enabled).
- Confirm operator checklist items:
  - Tool is properly fitted on the machine.
  - Machine head is positioned at the top-left corner of the chip (origin).
  - Tool is at the correct working height above the chip surface.
  - No obstacles are present on or around the chip scanning area.
- Confirm config values are correct:
  - `xyz-stage/configuration/scan.py`
  - `xyz-stage/configuration/machine.py`
  - `Configuration/measurement/output.py`
  - `Configuration/measurement/pico.py`
  - `Configuration/measurement/target.py`
  - `Configuration/measurement/runtime.py`
- Confirm output root path is writable.

Optional quick sanity:

```bash
python -m compileall xyz-stage MeasurementScripts Common Configuration Helpers
```

```bash
python -c "import colorama,requests,tqdm,numpy,trsfile,picosdk"
```

Before full scan:
- OctoPrint reachable at configured URL (if motion is enabled).
- `API_KEY_OCTO` set in the same shell (if motion is enabled).
- PicoScope detected by OS and usable (if PicoScope is enabled).
- CWNano connected and firmware responding (if ChipWhisperer is enabled).
- Output directory in `xyz-stage/configuration/scan.py` exists or is creatable.

PicoScope parameter reference (ranges, channels, trigger/timebase details):
- https://www.picotech.com/download/manuals/picoscope-3000-series-programmers-guide.pdf

## 2) Runtime mode selection (real vs dry-run)

Three independent toggles:
- Motion: `xyz-stage/configuration/machine.py`
  - `MACHINE_ENABLE_MOTION = True|False`
- PicoScope: `Configuration/measurement/runtime.py`
  - `RUNTIME_ENABLE_PICOSCOPE = True|False`
- ChipWhisperer: `Configuration/measurement/runtime.py`
  - `RUNTIME_ENABLE_CHIPWHISPERER = True|False`

Recommended presets:
- Full hardware run: all three `True`
- Motion-only dry-run: motion `False`, Pico/CW `True`
- Capture-only dry-run: Pico `False`, CW `False` (fast orchestration test)
- Full dry-run: all three `False`

At startup, the program prints warnings when any subsystem is disabled.

## 3) Start a run

From repository root:

```bash
python xyz-stage/main.py
```

The runtime flow is:
1. Load scanner + measurement config.
2. Apply printer settings (if motion enabled).
3. Optional chip-size picking when chip size is unset/non-positive.
4. Scan preview confirmation.
5. Scanning loop and trace capture.
6. Scan overview generation.
7. Exploration/evaluation phase.

## 4) Operator controls during run

### Setup and chip-size picking
- Follow prompts.
- If chip size is unset/non-positive, interactive corner picking starts.

### Calibration controls
- `w/s`: +/-0.1 mm
- `W/S`: +/-1.0 mm
- `f/v`: +/-5.0 mm
- `c`: confirm corner height
- `q`: cancel calibration

### Evaluation phase controls
- `list`: list scanned points
- `goto N`: move to point index `N`
- `move X Y`: move to absolute XY
- `plot`: plot trace for currently selected point
- `plot N`: plot trace for point index `N`
- `heatmap`: plot point-wise heatmap using absolute trace strength (`mean(abs(samples))`)
- `exit` or `quit`: end evaluation and disable steppers

### Direct G-code command (advanced)
- Repository support exists for direct command send via `send_gcode_command(...)` in `xyz-stage/octoprint_communication.py`.
- This is not an interactive evaluation-phase command; use it as a direct Python call when needed.
- Example from `xyz-stage` directory:

```bash
python -c "from octoprint_communication import send_gcode_command; send_gcode_command('M114')"
```

## 5) Failure behavior

If a trace capture fails at any point:
- Scan stops immediately.
- Run transitions to overview/evaluation with collected partial results.

This is intentional fail-fast behavior to avoid collecting mixed-quality datasets.

Operator recovery steps:
1. Record the exact failing position and timestamp.
2. Check startup warnings to confirm whether any dry-run toggle was enabled unintentionally.
3. Verify hardware state (probe position, Pico trigger wiring, CWNano connectivity, OctoPrint status).
4. Re-run after the issue is fixed; a new sequential run folder is created automatically.
5. Mark partial runs clearly in your thesis notes and do not mix them with full runs.

## 6) Outputs to verify after run

Primary output locations:
- Scan output root from `xyz-stage/configuration/scan.py`
- Run folder naming and point trace naming are controlled by scanner runtime:
  - Run folder: next numeric index under output root (`1`, `2`, `3`, ...)
  - Trace files: point index (`0.trs`, `1.trs`, ...)

Verify:
- Output folder exists for this run index.
- Trace files exist and are non-empty.
- `scan_settings.txt` exists and matches intended run settings.
- Number of successful points matches expectation (or documented early stop).

## 7) Common operator mistakes

- Running with wrong venv.
- Forgetting to set `API_KEY_OCTO` in the active shell.
- Accidentally leaving dry-run toggles enabled for hardware runs.
- Editing scan/machine config but not measurement config (or vice versa).
- Ignoring startup warnings about disabled subsystems.

## 8) Recommended run log notes (for thesis rigor)

For each run, note:
- Date/time and operator name.
- Git commit hash.
- Toggle states (`enable_motion`, `enable_picoscope`, `enable_chipwhisperer`).
- Chip/board identifier and physical setup notes.
- Any interruptions/failures and whether run was partial.
