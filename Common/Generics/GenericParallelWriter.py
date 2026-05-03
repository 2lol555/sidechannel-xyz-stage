import numpy as np
import trsfile
from trsfile import Trace
from multiprocessing.shared_memory import SharedMemory
from Common.Generics.GenericTraceWriter import GenericTraceWriter
from Configuration.Models.Traces.ParallelWriterConfigModel import ParallelWriterConfigModel
from numpy.typing import NDArray


class GenericParallelWriter(GenericTraceWriter):

    def __init__(self, multithreading_config: ParallelWriterConfigModel):
        self.process_count: int = multithreading_config.process_count
        self.data_shm_name: str = multithreading_config.data_shm_name
        self.traces_shm_name: str = multithreading_config.traces_shm_name
        super().__init__(multithreading_config.writer_config)
        self._perform_parallel_checks()
        self._prepare_shared_memory()

    def _perform_parallel_checks(self):
        assert self.process_count > 0, 'Process count must be positive'

    def cleanup(self) -> None:
        self.free_shared_memory(self.data_shm_name)
        self.free_shared_memory(self.traces_shm_name)
        super().cleanup()

    def _prepare_shared_memory(self) -> None:
        if not self.is_output_numpy:
            return
        traces_shm_size: int = self.process_count * self.output_trace_length * self.output_sample_coding.itemsize
        self.allocate_shared_memory(self.traces_shm_name, traces_shm_size)
        if not self.is_input_numpy: # If not numpy, we need to copy data from every trace processed
            self.allocate_shared_memory(self.data_shm_name, self.process_count * self.data_length)

    def copy_from_shared_memory(self, current_index: int, current_process_count: int, current_batch: int = -1,
                                include_indexes: NDArray[np.int32] = None) -> None:
        """
        Copy trace data from shared memory to output (Used only if output is numpy)
        current_index: is the index of the output without discarded traces up to this point
        current_process_count: is the number of traces in the current batch
        current_batch: Batch start index of currently process input (necessary when input is numpy and index filtering)
        include_indexes: contain indexes of traces which will be included in output from current_index, None include all
        """
        if not self.is_output_numpy:
            return
        if self.is_input_numpy:
            if current_batch == -1:
                if include_indexes is not None:
                    raise Exception('Batch must be defined when input is numpy and index filtering is used')
                current_batch = current_index
            data: NDArray[np.uint8] = self.data[current_batch:current_batch + current_process_count]
        else:
            data_shm: SharedMemory = SharedMemory(name=self.data_shm_name)
            data = np.ndarray((current_process_count, self.data_length), dtype='uint8', buffer=data_shm.buf)
        if include_indexes is None:
            include_indexes = np.arange(current_process_count) # Include all traces in the current batch
        self.output_data[current_index:current_index + len(include_indexes)] = data[include_indexes]
        traces_shm: SharedMemory = SharedMemory(name=self.traces_shm_name)
        traces: NDArray = np.ndarray((current_process_count, self.output_trace_length),
                                     dtype=self.output_sample_coding, buffer=traces_shm.buf)
        self.output_traces[current_index:current_index + len(include_indexes)] = traces[include_indexes]

    def check_process_bounds(self, index: int, use_input_trace_count: bool = False) -> int:
        """
        Check if the process count is larger than necessary to work with remaining samples from
        the index if yes lowers it.
        """
        process_count: int = self.process_count
        trace_count: int = self.trace_count if use_input_trace_count else self.output_trace_count
        if index + process_count > trace_count:
            process_count = trace_count - index
        return process_count

    # Needs to be static so it can be used in multithreaded code
    @staticmethod
    def copy_data_from_trace(shared_memory_name: str, process_count: int, trace: Trace, trace_idx: int) -> None:
        data_length: int = trace.headers.get(trsfile.Header.LENGTH_DATA)
        data_shm: SharedMemory = SharedMemory(name=shared_memory_name)
        data_samples_shm: NDArray[np.uint8] = np.ndarray(data_length, dtype='uint8', buffer=data_shm.buf,
                                                         offset=(trace_idx % process_count) * data_length)
        data_shift: int = 0
        for parameter in trace.parameters.values():
            data_samples_shm[data_shift:data_shift + len(parameter.value)] = parameter.value
            data_shift += len(parameter.value)

    @staticmethod
    def free_shared_memory(shared_memory_name: str) -> None:
        """
        Helper method to free shared memory by name
        """
        try:
            data_shm: SharedMemory = SharedMemory(shared_memory_name)
            data_shm.unlink()
            data_shm.close()
        except FileNotFoundError:
            pass

    @staticmethod
    def allocate_shared_memory(shm_name: str, shm_size: int) -> None:
        """
         Helper method to allocate shared memory by name and size
        """
        try:
            existing_shm = SharedMemory(shm_name)
            existing_shm.unlink()  # Unlink existing shared memory to create a new one
            existing_shm.close()
        except FileNotFoundError:
            pass  # Shared memory does not exist, proceed to create a new one
        SharedMemory(name=shm_name, create=True, size=shm_size)
