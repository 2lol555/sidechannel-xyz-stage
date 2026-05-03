from numbers import Real
from typing import Dict, Mapping, Tuple

from configuration.machine import get_machine_settings
from configuration.scan import get_scan_settings
from configuration.schema import RuntimeConfig


_AXES_XYZE = ("X", "Y", "Z", "E")
_AXES_XYZ = ("X", "Y", "Z")


def _as_tuple2(name: str, value: Tuple[float, float]) -> Tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise RuntimeError(f"{name} must contain exactly two numeric values.")
    x, y = value
    if not isinstance(x, Real) or not isinstance(y, Real):
        raise RuntimeError(f"{name} values must be numeric.")
    return float(x), float(y)


def _as_axis_map(name: str, value: Mapping[str, float], axes: Tuple[str, ...]) -> Dict[str, float]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{name} must be a dict-like mapping.")
    out: Dict[str, float] = {}
    for axis in axes:
        if axis not in value:
            raise RuntimeError(f"{name} must define axis '{axis}'.")
        axis_value = value[axis]
        if not isinstance(axis_value, Real):
            raise RuntimeError(f"{name}[{axis}] must be numeric.")
        out[axis] = float(axis_value)
    return out


def _as_axis_flip_map(name: str, value: Mapping[str, bool], axes: Tuple[str, ...]) -> Dict[str, bool]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{name} must be a dict-like mapping.")
    out: Dict[str, bool] = {}
    for axis in axes:
        if axis not in value:
            raise RuntimeError(f"{name} must define axis '{axis}'.")
        axis_value = value[axis]
        if not isinstance(axis_value, bool):
            raise RuntimeError(f"{name}[{axis}] must be boolean (True=flip, False=normal).")
        out[axis] = axis_value
    return out


def _validate_config(cfg: RuntimeConfig) -> None:
    if cfg.chip_size[0] < 0 or cfg.chip_size[1] < 0:
        raise RuntimeError("chip_size values must be >= 0.")
    if cfg.step_size[0] <= 0 or cfg.step_size[1] <= 0:
        raise RuntimeError("step_size values must be > 0.")

    for axis in _AXES_XYZE:
        if cfg.steps_per_mm[axis] <= 0:
            raise RuntimeError(f"steps_per_mm[{axis}] must be > 0.")
        if cfg.max_feedrate[axis] <= 0:
            raise RuntimeError(f"max_feedrate[{axis}] must be > 0.")

    if not isinstance(cfg.octoprint_url, str) or not cfg.octoprint_url.strip():
        raise RuntimeError("octoprint_url must be a non-empty string.")
    if not isinstance(cfg.api_key_env, str) or not cfg.api_key_env.strip():
        raise RuntimeError("api_key_env must be a non-empty string.")
    if not isinstance(cfg.output_root, str) or not cfg.output_root.strip():
        raise RuntimeError("output_root must be a non-empty string.")
    if not isinstance(cfg.acceleration, Real):
        raise RuntimeError("acceleration must be numeric.")
    if not isinstance(cfg.hop_height, Real) or cfg.hop_height < 0:
        raise RuntimeError("hop_height must be numeric and >= 0.")
    if not isinstance(cfg.enable_motion, bool):
        raise RuntimeError("enable_motion must be boolean.")


def build_runtime_config() -> RuntimeConfig:
    scan_cfg = get_scan_settings()
    machine_cfg = get_machine_settings()

    cfg = RuntimeConfig(
        chip_size=_as_tuple2("chip_size", scan_cfg.chip_size),
        step_size=_as_tuple2("step_size", scan_cfg.step_size),
        output_root=scan_cfg.output_root,
        steps_per_mm=_as_axis_map("steps_per_mm", machine_cfg.steps_per_mm, _AXES_XYZE),
        max_feedrate=_as_axis_map("max_feedrate", machine_cfg.max_feedrate, _AXES_XYZE),
        acceleration=float(machine_cfg.acceleration),
        hop_height=float(machine_cfg.hop_height),
        axis_directions=_as_axis_flip_map("axis_directions", machine_cfg.axis_directions, _AXES_XYZ),
        octoprint_url=machine_cfg.octoprint_url,
        api_key_env=machine_cfg.api_key_env,
        enable_motion=bool(machine_cfg.enable_motion),
    )
    _validate_config(cfg)
    return cfg
