import os

from dataclasses import dataclass
from typing import Optional

from side_channel_types import Position

from MeasurementScripts.MeasureScriptPicoscopeJC import runTraceCapture, setupTraceCapture, MeasureScriptPicoscopeJC, \
    cleanupTraceCapture


@dataclass
class PayloadContext:
    picoscope: MeasureScriptPicoscopeJC
    output_folder: str


def _next_sequential_output_folder(output_root: str) -> str:
    os.makedirs(output_root, exist_ok=True)
    max_numeric_folder = 0
    for entry in os.listdir(output_root):
        full_path = os.path.join(output_root, entry)
        if os.path.isdir(full_path) and entry.isdigit():
            max_numeric_folder = max(max_numeric_folder, int(entry))
    return os.path.join(output_root, str(max_numeric_folder + 1))


def _remove_bootstrap_output_file(pico: MeasureScriptPicoscopeJC) -> None:
    """Delete the initial default output file created by script construction."""
    bootstrap_path = getattr(pico, "output_path", None)
    if not bootstrap_path:
        return

    traceset = getattr(pico, "output_traceset", None)
    if traceset is not None:
        traceset.close()
        pico.output_traceset = None

    if os.path.exists(bootstrap_path):
        try:
            os.remove(bootstrap_path)
        except OSError:
            # Non-fatal: scan can continue; only bootstrap cleanup failed.
            pass


def setup_payload(output_root: str) -> PayloadContext:
    folder_path = _next_sequential_output_folder(output_root)
    os.makedirs(folder_path, exist_ok=True)
    pico = setupTraceCapture(output_folder=folder_path)
    _remove_bootstrap_output_file(pico)
    res = PayloadContext(picoscope=pico, output_folder=folder_path)
    return res

def run_payload(ctx: PayloadContext, point_index: int, coords: Position) -> Optional[str]:
    del coords
    filename = str(point_index)
    runTraceCapture(ctx.picoscope, filename)
    if not getattr(ctx.picoscope, "enable_picoscope", True):
        return None
    return getattr(ctx.picoscope, "output_path", None)

def cleanup_payload(ctx: PayloadContext) -> None:
    cleanupTraceCapture(ctx.picoscope)
