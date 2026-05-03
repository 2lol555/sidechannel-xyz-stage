import numpy as np
from typing import Tuple
from numpy.typing import NDArray


class ConditionalAverager:

    def __init__(self, num_values: int, trace_length: int):
        """Allocate the matrix of averaged Traces"""
        self._avtraces = np.zeros((num_values, trace_length), dtype='float64')
        self._counters = np.zeros(num_values, dtype='uint32')

    def add_trace(self, data: int, trace: NDArray) -> None:
        """Add a single trace with a corresponding single chunk of data"""
        if self._counters[data] == 0:
            self._avtraces[data] = trace
            self._counters[data] += 1
        else:
            self._counters[data] += 1
            self._avtraces[data] = self._avtraces[data] + (trace - self._avtraces[data]) / self._counters[data]

    def get_snapshot(self) -> Tuple[NDArray[np.uint32], NDArray]:
        """Return a snapshot of the average matrix"""
        avdata_snap: NDArray = np.flatnonzero(self._counters)   # get a vector of only _observed_ values
        avtraces_snap: NDArray = self._avtraces[avdata_snap] # remove lines corresponding to non-observed values
        return avdata_snap, avtraces_snap

    def reset(self) -> None:
        self._avtraces.fill(0)
        self._counters.fill(0)
