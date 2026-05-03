"""Capture a dedicated CPA trace set at the current XYZ position.

This script does not move the stage. It only performs acquisition using the
existing PicoScope + CWNano measurement pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from secrets import token_bytes
import time
import copy

from config import get_output_root, load_config_from_file
from logger import error, header, info, success
from MeasurementScripts.MeasureScriptPicoscopeJC import (
    MeasureScriptPicoscopeJC,
    cleanupTraceCapture,
)
from Configuration.measurement import MEASUREMENT_CONFIG


def _next_sequential_output_folder(output_root: str) -> str:
    os.makedirs(output_root, exist_ok=True)
    max_numeric_folder = 0
    for entry in os.listdir(output_root):
        full_path = os.path.join(output_root, entry)
        if os.path.isdir(full_path) and entry.isdigit():
            max_numeric_folder = max(max_numeric_folder, int(entry))
    return os.path.join(output_root, str(max_numeric_folder + 1))


def _parse_key_hex(key_hex: str | None) -> bytes:
    if key_hex is None:
        return token_bytes(16)
    normalized = key_hex.strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    if len(normalized) != 32:
        raise ValueError("key_hex must be exactly 32 hex chars (16 bytes).")
    return bytes.fromhex(normalized)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture dedicated CPA traces at current XYZ position (no movement)."
    )
    parser.add_argument(
        "--point-index",
        type=int,
        default=768,
        help="Logical point index used in filename metadata (default: 768).",
    )
    parser.add_argument(
        "--trace-count",
        type=int,
        default=5000,
        help="Number of traces to capture (default: 5000).",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="Output filename stem (without extension). Default: '<point-index>_cpa'.",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        default=None,
        help="Optional explicit output folder. If omitted, next numeric folder is created under output_root.",
    )
    parser.add_argument(
        "--key-hex",
        type=str,
        default=None,
        help="Optional 16-byte AES key as hex. If omitted, a random key is generated and reported.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.trace_count <= 0:
        raise ValueError("--trace-count must be > 0.")

    load_config_from_file()
    output_root = get_output_root()
    output_folder = args.output_folder or _next_sequential_output_folder(output_root)
    filename = args.filename or f"{args.point_index}_cpa"
    fixed_key = _parse_key_hex(args.key_hex)

    os.makedirs(output_folder, exist_ok=True)
    header("CPA Dedicated Capture (No Movement)")
    info(f"Current stage position: unchanged (no XY move).")
    info(f"Point index label: {args.point_index}")
    info(f"Trace count: {args.trace_count}")
    info(f"Output folder: {output_folder}")
    info(f"Output filename: {filename}.trs")
    info(f"AES key (fixed): 0x{fixed_key.hex().upper()}")

    measurement_config = copy.deepcopy(MEASUREMENT_CONFIG)
    measurement_config.output.output_folder_path = output_folder
    measurement_config.output.output_file_name = filename
    measurement_config.output.trace_count = int(args.trace_count)

    measure_script = MeasureScriptPicoscopeJC(measurement_config)

    try:
        measure_script.prepare_output(filename)
        measure_script.key = fixed_key
        if measure_script.enable_chipwhisperer:
            measure_script.cw.set_key(measure_script.key)

        start_time = time.time()
        save_traces = measure_script.enable_picoscope

        # Keep the same arming sequence as the core script.
        measure_script._encrypt_and_capture(bytes(16), -1, save=False)

        for index in range(measure_script.output_trace_count):
            plaintext = token_bytes(measure_script.key_length_bytes)
            if index % 10 == 0 or index == measure_script.output_trace_count - 1:
                info(f'Capturing trace {index + 1}/{measure_script.output_trace_count}...')
            measure_script._encrypt_and_capture(plaintext, index, save=save_traces)

        if save_traces:
            measure_script.save_output()
        elapsed = time.time() - start_time
        info(f"Total execution time: {elapsed:.2f} seconds")

        trace_path = getattr(measure_script, "output_path", None)
        metadata = {
            "point_index": int(args.point_index),
            "trace_count": int(args.trace_count),
            "plaintext_mode": "random",
            "fixed_key_hex": fixed_key.hex().upper(),
            "trace_path": trace_path,
            "output_folder": output_folder,
            "filename_stem": filename,
        }
        metadata_path = Path(output_folder) / f"{filename}_capture_meta.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        success(f"Capture completed. Trace file: {trace_path}")
        success(f"Metadata written: {metadata_path}")
    except Exception as exc:
        error(f"Capture failed: {type(exc).__name__}: {exc}")
        raise
    finally:
        cleanupTraceCapture(measure_script)


if __name__ == "__main__":
    main()
