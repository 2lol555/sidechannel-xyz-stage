from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ScanSettings:
    chip_size: Tuple[float, float]
    step_size: Tuple[float, float]
    output_root: str


@dataclass
class MachineSettings:
    steps_per_mm: Dict[str, float]
    max_feedrate: Dict[str, float]
    acceleration: float
    hop_height: float
    axis_directions: Dict[str, bool]
    octoprint_url: str
    api_key_env: str
    enable_motion: bool


@dataclass
class RuntimeConfig:
    chip_size: Tuple[float, float]
    step_size: Tuple[float, float]
    output_root: str
    steps_per_mm: Dict[str, float]
    max_feedrate: Dict[str, float]
    acceleration: float
    hop_height: float
    axis_directions: Dict[str, bool]
    octoprint_url: str
    api_key_env: str
    enable_motion: bool
