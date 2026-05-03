from dataclasses import dataclass
from trsfile import Trace
from numpy.typing import NDArray

@dataclass
class AlignmentInterval:
    interval_samples: NDArray
    trace: Trace | None
    cut_start_index: int
    alignment_start_index: int
    original_samples: NDArray | None # Used only in advanced alignment
