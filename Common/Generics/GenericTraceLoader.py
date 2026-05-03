from os.path import splitext
import trsfile
import atexit
import signal
import sys
import functools
import numpy as np
from numpy.typing import NDArray
from trsfile import TraceSet
from typing import Tuple
from Common.Models.FileType import FileType
from Configuration.Constants import DATA_NAME, TRACES_NAME
from Configuration.Models.Traces.TraceLoaderConfigModel import TraceLoaderConfigModel
from Helpers.FileNamingHelper import get_data_path


class GenericTraceLoader:

    def __init__(self, loader_config: TraceLoaderConfigModel, max_trace_count: int | None = None) -> None:
        self.target_path: str = loader_config.target_path
        self.data_path: str = get_data_path(loader_config.data_path, self.target_path)
        self.input_type: FileType = self._get_extension_of_file()
        self.data, self.traces, self.traceset = self._load_data_traces()
        self.register_cleanup()
        self.is_input_numpy: bool = self.input_type == FileType.NPZ or self.input_type == FileType.NPY
        self.max_trace_count: int = max_trace_count
        self.trace_count, self.data_length, self.trace_length, self.sample_coding = self._update_metadata()
        if self.max_trace_count is None:
            self.max_trace_count = self.trace_count
        self.headers: dict | None = None if self.traceset is None else self.traceset.get_headers().copy()

    def register_cleanup(self) -> None:
        def handle_signal(signum, frame):
            self.cleanup()
            sys.exit(0)
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def cleanup(self):
        if self.traceset is not None:
            self.traceset.close()
        if self.data is not None:
            del self.data
            self.data = None
        if self.traces is not None:
            del self.traces
            self.traces = None

    def _update_metadata(self) -> Tuple[int, int, int, np.dtype]:
        if self.input_type == FileType.TRS:
            trace_count: int = self.traceset.get_header(trsfile.Header.NUMBER_TRACES)
            data_length: int = self.traceset.get_header(trsfile.Header.LENGTH_DATA)
            trace_length: int = self.traceset.get_header(trsfile.Header.NUMBER_SAMPLES)
            sample_coding: np.dtype = np.dtype(self.traceset.get_header(trsfile.Header.SAMPLE_CODING).format)
        elif self.is_input_numpy:
            trace_count = self.traces.shape[0]
            data_length = self.data.shape[1]
            trace_length = self.traces.shape[1]
            sample_coding = self.traces.dtype
        else:
            raise Exception('Unsupported file type')
        assert self.data is None or self.data.shape[0] == trace_count, 'Data count does not match trace count'
        assert self.max_trace_count is None or self.max_trace_count >= trace_count, 'Invalid max trace count'
        return trace_count, data_length, trace_length, sample_coding

    def _load_data_traces(self) -> Tuple[NDArray | None, NDArray | None, TraceSet | None]:
        data: NDArray | None = None
        traces: NDArray | None = None
        traceset: TraceSet | None = None
        match self.input_type:
            case FileType.TRS:
                traceset = trsfile.open(self.target_path, 'r')
            case FileType.NPZ:
                data = np.load(self.target_path, mmap_mode=None)[DATA_NAME]
                traces = np.load(self.target_path, mmap_mode=None)[TRACES_NAME]
            case FileType.NPY:
                data = np.load(self.data_path, mmap_mode='r')
                traces = np.load(self.target_path, mmap_mode='r')
            case _:
                raise Exception(f'Unsupported target file type {self.input_type}')
        return data, traces, traceset

    def _get_extension_of_file(self) -> FileType:
        file_extension: str = splitext(self.target_path)[1]
        match file_extension:
            case '.npz':
                return FileType.NPZ
            case '.npy':
                if self.data_path != '':
                    data_extension: str = splitext(self.data_path)[1]
                    assert data_extension == '.npy', 'Invalid data extension (must be npy)'
                return FileType.NPY
            case '.trs':
                return FileType.TRS
            case _:
                raise Exception('Unable to determine input file type')

    def reload_file(self) -> None:
        print('Reloading files...', end='', flush=True)
        if self.traceset is not None:
            self.traceset.close()
        if self.input_type == FileType.TRS:
            self.traceset = trsfile.open(self.target_path, 'r')
        elif self.input_type == FileType.NPY:
            self.data = np.load(self.data_path, mmap_mode='r')
            self.traces = np.load(self.target_path, mmap_mode='r')
        else:
            self.data = np.load(self.target_path, mmap_mode=None)[TRACES_NAME]
            self.traces = np.load(self.target_path, mmap_mode=None)[TRACES_NAME]
        self.trace_count, self.data_length, self.trace_length, self.sample_coding = self._update_metadata()
        print('done', flush=True)
