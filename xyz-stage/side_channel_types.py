"""Shared scan types.

This project uses a few common concepts (2D positions, chip sizes, scan results)
across multiple modules. Centralizing the aliases reduces typing noise and keeps
signatures readable.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, TypeAlias


Position: TypeAlias = Tuple[float, float]
ChipSize: TypeAlias = Tuple[float, float]
StepSize: TypeAlias = Tuple[float, float]

CornerHeights: TypeAlias = Dict[Position, float]


@dataclass(frozen=True)
class ScanPointResult:
    ok: bool
    trace_path: Optional[str] = None


ScanResults: TypeAlias = Dict[Position, ScanPointResult]
