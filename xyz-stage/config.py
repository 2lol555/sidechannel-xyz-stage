"""Load and expose scanner configuration."""

from typing import Any, Dict, Optional, Tuple

from configuration.build import build_runtime_config
from logger import success

# Fallbacks for partially specified machine axis dicts in command emitters.
DEFAULT_STEPS_PER_MM: Dict[str, float] = {"X": 1600.0, "Y": 1600.0, "Z": 800.0, "E": 325.0}
DEFAULT_MAX_FEEDRATE: Dict[str, float] = {"X": 2.5, "Y": 2.5, "Z": 2.5, "E": 1.0}
DEFAULT_ACCELERATION: float = 2.0

_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _to_dict() -> Dict[str, Any]:
    cfg = build_runtime_config()
    return {
        "chip_size": cfg.chip_size,
        "step_size": cfg.step_size,
        "output_root": cfg.output_root,
        "steps_per_mm": cfg.steps_per_mm,
        "max_feedrate": cfg.max_feedrate,
        "acceleration": cfg.acceleration,
        "hop_height": cfg.hop_height,
        "axis_directions": cfg.axis_directions,
        "octoprint_url": cfg.octoprint_url,
        "api_key_env": cfg.api_key_env,
        "enable_motion": cfg.enable_motion,
    }


def load_config_from_file(
    scan_module: str = "configuration.scan",
    machine_module: str = "configuration.machine",
) -> Dict[str, Any]:
    """Load runtime config from configuration modules."""
    del scan_module
    del machine_module
    global _CONFIG_CACHE
    _CONFIG_CACHE = _to_dict()
    success("Loaded configuration from configuration/scan.py and configuration/machine.py")
    return _CONFIG_CACHE


def get_config() -> Dict[str, Any]:
    """Return loaded config, loading it on first access."""
    if _CONFIG_CACHE is None:
        return load_config_from_file()
    return _CONFIG_CACHE


def set_chip_size(chip_size: Tuple[float, float]) -> None:
    """Override chip_size in cached config (used by interactive setup)."""
    cfg = get_config()
    if not isinstance(chip_size, (tuple, list)) or len(chip_size) != 2:
        raise RuntimeError("chip_size must contain exactly two numeric values.")
    cfg["chip_size"] = (float(chip_size[0]), float(chip_size[1]))


def get_chip_size() -> Tuple[float, float]:
    cfg = get_config()
    return cfg["chip_size"]


def get_step_size() -> Tuple[float, float]:
    cfg = get_config()
    return cfg["step_size"]


def get_output_root() -> str:
    cfg = get_config()
    return cfg["output_root"]
