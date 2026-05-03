import math
import numpy as np
import trsfile
from typing import Tuple
from trsfile import TraceSet, Header
from numpy.typing import NDArray
from Common.Generics.GenericTraceLoader import GenericTraceLoader
from Common.Maps.TypeMaps import dtype_converter_map
from Common.Models.FileType import FileType
from Common.Models.PathType import PathType
from Configuration.Models.Traces.TraceWriterConfigModel import TraceWriterConfigModel
from Helpers.FileNamingHelper import get_alignment_output_paths, get_resampler_output_paths, get_converter_output_paths
from Helpers.GenericHelper import check_interval
from Helpers.IntervalHelpers import calculate_output_length
from Helpers.NumpyHelper import remove_rows_numpy


class GenericTraceWriter(GenericTraceLoader):

    def __init__(self, writer_config: TraceWriterConfigModel) -> None:
        self.output_traceset: TraceSet | None = None
        self.data_output_path: str | None = None
        self.output_path: str | None = None
        self.output_data: NDArray[np.uint8] | None = None
        self.output_traces: NDArray | None = None
        super().__init__(writer_config.loader_config)
        self.output_type: FileType = writer_config.output_type
        self.output_folder: str = writer_config.output_folder
        self.output_trace_count: int = calculate_output_length(writer_config.output_trace_count, self.trace_count)
        self.output_trace_length: int = calculate_output_length(writer_config.output_trace_length, self.trace_length)
        if writer_config.divide_output_length_by > 1:
            self.divide_output_length_by: int = writer_config.divide_output_length_by
            self.output_trace_length = math.floor(self.output_trace_length / self.divide_output_length_by)
        else:
            self.divide_output_length_by = 1 # Prevent invalid configuration
        self.output_sample_coding: np.dtype = writer_config.output_sample_coding
        if self.output_sample_coding is None:
            self.output_sample_coding = self.sample_coding
        self.output_path_type: PathType = writer_config.path_type
        self.is_compressed: bool = writer_config.output_compressed
        self.is_output_numpy = self.output_type == FileType.NPZ or self.output_type == FileType.NPY

    def cleanup(self):
        if self.output_traceset is not None:
            self.output_traceset.close()
        if self.output_data is not None:
            del self.output_data
            self.output_data = None
        if self.output_traces is not None:
            del self.output_traces
            self.output_traces = None
        super().cleanup()

    def _get_output_paths(self, cut_from: int = 0, cut_to: int = 0, include_cut: bool = False) -> Tuple[str, str]:
        match self.output_path_type:
            case PathType.Alignment:
                return get_alignment_output_paths(self.target_path, self.output_type, self.output_folder,
                                                  cut_from, cut_to, include_cut)
            case PathType.Resampler:
                return get_resampler_output_paths(self.target_path, self.output_type, self.output_folder,
                                                  cut_from, cut_to, include_cut)
            case PathType.Converter:
                return get_converter_output_paths(self.target_path, self.output_type, self.output_folder,
                                                  cut_from, cut_to, include_cut)
            case _:
                raise Exception(f'Unknown path type: {self.output_path_type}')


    def _prepare_path(self, cut_from: int, cut_to: int, include_cut: bool) -> None:
        check_interval(cut_from, cut_to, self.trace_length)
        current_output_length: int = math.floor((cut_to - cut_from) / self.divide_output_length_by)
        assert self.output_trace_length == current_output_length, (
            f'Trace length must be consistent across different calls => current: {current_output_length},'
            f' initialized with {self.output_trace_length}')
        include_cut: bool = include_cut and not (cut_from == 0 and cut_to == self.trace_length)
        if include_cut:
            self.data_output_path, self.output_path = self._get_output_paths(cut_from, cut_to, include_cut)
            return
        if self.data_output_path is None or self.output_path is None:
            self.data_output_path, self.output_path = self._get_output_paths()

    def create_output(self, cut_from: int, cut_to: int, include_cut: bool = False) -> None:
        """
        Create output files and allocate memory for output data and traces
        """
        self._prepare_path(cut_from, cut_to, include_cut)
        print('Allocating files...', end='', flush=True)
        if self.output_type == FileType.NPY:
            self.output_data = np.lib.format.open_memmap(self.data_output_path, 'w+', 'uint8',
                                                         (self.output_trace_count, self.data_length))
            # Memory mapped files do not allow changing shape, so we need to allocate maximum possible memory
            # and truncate a file after we know how many traces will be kept after alignment.
            self.output_traces = np.lib.format.open_memmap(self.output_path, 'w+', self.output_sample_coding,
                                                           (self.output_trace_count, self.output_trace_length))
        elif self.output_type == FileType.NPZ:
            if self.output_data is None: # NPZ file does not need to reallocate
                self.output_data = np.empty((self.output_trace_count, self.data_length), 'uint8')
            if self.output_traces is None:
                self.output_traces = np.empty((self.output_trace_count, self.output_trace_length),
                                              self.output_sample_coding)
        elif self.output_type == FileType.TRS:
            if self.is_input_numpy:
                headers = {
                    Header.TRS_VERSION: 2,
                    Header.NUMBER_SAMPLES: self.output_trace_length,
                    Header.LENGTH_DATA: self.data_length,
                }
                self.headers = headers.copy()
            else:
                headers: dict = self.headers.copy()
            headers[Header.NUMBER_TRACES] = 0  # Create an empty trace file
            headers[Header.NUMBER_SAMPLES] = self.output_trace_length
            headers[Header.SAMPLE_CODING] = dtype_converter_map[self.output_sample_coding.name]
            self.output_traceset = trsfile.open(self.output_path, 'w', padding_mode=trsfile.TracePadding.AUTO,
                                             headers=headers, live_update=False)
        else:
            raise Exception(f'Unsupported output type: {self.output_type}')
        print('done', flush=True)

    def save_output(self, discarded_trace_count: int = 0) -> None:
        output_trace_count: int = self.output_trace_count - discarded_trace_count
        print(f'Saving output to \"{self.output_path}\"...', end='', flush=True)
        if self.is_output_numpy and (self.output_data is None or self.output_traces is None):
            raise Exception(f'Numpy output not yet initialized')
        if self.output_type == FileType.TRS:
            if self.output_traceset is None:
                raise Exception(f'Output traceset not yet initialized')
            self.output_traceset.close()
            self.output_traceset = None # Prevent double free and signal to reset trs if called again
        elif self.output_type == FileType.NPZ:
            data: NDArray = self.output_data[:output_trace_count]
            traces: NDArray = self.output_traces[:output_trace_count]
            if self.is_compressed:
                np.savez_compressed(self.output_path, traces=traces, data=data)
            else:
                np.savez(self.output_path, traces=traces, data=data)
        elif self.output_type == FileType.NPY:
            self.output_data.flush()
            self.output_traces.flush()
            if discarded_trace_count > 0:
                # Remove memory-mapped arrays to safely modify the file and remove redundant data/traces
                self.output_data = None # 
                self.output_traces = None
                remove_rows_numpy(self.data_output_path, self.output_trace_count,
                                  discarded_trace_count, self.data_length)
                remove_rows_numpy(self.output_path, self.output_trace_count,
                                  discarded_trace_count, self.output_trace_length * self.sample_coding.itemsize)
        else:
            raise Exception(f'Unsupported output type: {self.output_type}')
        print('done', flush=True)
