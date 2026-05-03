# XYZ Stage Scanner - Getting Started

This guide is for running the scanner workflow from `xyz-stage/main.py`.
It combines the environment setup from the repository root `README.md` with the current xyz-stage runtime flow.

## 1) Install Python (Windows)

If Python is not installed yet, install Python 3.13 first.

```powershell
winget install Python.Python.3.13
```

Reopen PowerShell and verify:

```powershell
py -3.13 --version
```

## 2) Create and activate a virtual environment

Use Python 3.13.x (as in the root README).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Install Python dependencies

Minimum packages used by the current scanner + measurement flow:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install numpy trsfile tqdm requests colorama picosdk chipwhisperer pycryptodome matplotlib
```

Notes:
- `smartleia` / `smartleia-target` are not needed for the current CWNano + Pico flow.
- `matplotlib` is used by `sca-helpers/plot.py` in evaluation mode.

## 4) Set `PYTHONPATH` to repo root

From repo root:

```bash
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

On Windows PowerShell (current shell):

```powershell
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
```

## 5) Configure scanner settings

Edit:
- `xyz-stage/configuration/scan.py` (chip size, step size, output root)
- `xyz-stage/configuration/machine.py` (OctoPrint URL, API key env var name, feedrates, acceleration, hop height, axis directions)
- `Configuration/measurement/output.py` (trace count/window/type; folder and per-point filename are set by scanner runtime)
- `Configuration/measurement/pico.py` (Pico trigger/channel/timebase/range)
- `Configuration/measurement/target.py` (CWNano capture timing and crypto I/O settings)
- `Configuration/measurement/runtime.py` (timeouts + dry-run toggles)

Set the API key environment variable expected by `xyz-stage/configuration/machine.py` (default `API_KEY_OCTO`).

Linux/macOS:

```bash
export API_KEY_OCTO="<your-octoprint-api-key>"
```

Windows PowerShell:

```powershell
$env:API_KEY_OCTO = "<your-octoprint-api-key>"
```

## 6) Run the scanner

From repository root:

```bash
python xyz-stage/main.py
```

Workflow summary:
- Loads config from `xyz-stage/configuration/scan.py` and `xyz-stage/configuration/machine.py`
- Applies printer motion settings via OctoPrint
- Runs optional interactive chip-size picking (only if chip size is unset/non-positive)
- Runs scan + capture payload
- Shows overview + evaluation phase

Output layout summary:
- Under `output_root`, each run is saved in the next numeric folder (`1`, `2`, `3`, ...).
- Per-point trace files are named by scan index: `0.trs`, `1.trs`, ... (matches evaluation `goto N` ordering).
- Each run folder includes `scan_settings.txt` and `scan_overview.png`.

Operator note:
- Direct OctoPrint G-code send support exists via `send_gcode_command(...)` in `xyz-stage/octoprint_communication.py` (advanced/manual usage).

## Dedicated CPA Capture At Current Position (No Movement)

If you already moved to the desired XY point (for example via evaluation `goto N`),
capture a dedicated random-plaintext set with fixed key and no motion:

```bash
python xyz-stage/capture_cpa_current_position.py --point-index 768 --trace-count 5000
```

Optional fixed key:

```bash
python xyz-stage/capture_cpa_current_position.py --point-index 768 --trace-count 5000 --key-hex 00112233445566778899AABBCCDDEEFF
```

Inspect trace shape first and select a 1-2 AES-round window:

```bash
python sca-helpers/plot.py /path/to/768_cpa.trs -n 5
```

Then run aggregate CPA rank-curve analysis on the selected window:

```bash
python sca-helpers/cpa_rank_curve.py --trs /path/to/768_cpa.trs --sample-from <START> --sample-to <END> --step 100
```

## Dry-run toggles

You can disable hardware subsystems independently:

- `xyz-stage/configuration/machine.py`
  - `MACHINE_ENABLE_MOTION = False` to skip all OctoPrint moves and gcode.
- `Configuration/measurement/runtime.py`
  - `RUNTIME_ENABLE_PICOSCOPE = False` to skip Pico communication and write synthetic traces.
  - `RUNTIME_ENABLE_CHIPWHISPERER = False` to skip CWNano commands.

## Optional: OctoPrint host installation on Linux

If you need to set up OctoPrint host on Linux, follow:
- https://octoprint.org/download/
- https://github.com/paukstelis/octoprint_deploy

## Pico tooling requirements

`pip install picosdk` installs Python bindings only.
You still need PicoScope system-level runtime/driver support so `picosdk.ps3000a` can talk to hardware.

Practical meaning:
- Keep `picosdk` in your venv.
- Also install PicoSDK/PicoScope drivers for your OS.
- Ensure the device is accessible (permissions/driver installation) before scanning.
