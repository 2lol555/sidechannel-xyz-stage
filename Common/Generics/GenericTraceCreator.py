import atexit
import numpy as np
import trsfile
import os
import sys
import signal
from typing import Tuple
from trsfile import TraceSet, Header
from numpy.typing import NDArray
from Common.Maps.TypeMaps import dtype_converter_map
from Common.Models.FileType import FileType
from Configuration.Models.Traces.TraceCreatorConfigModel import TraceCreatorConfigModel
from Helpers.ParameterWrapper import ParameterWrapper


class GenericTraceCreator:

    def __init__(self, generator_config: TraceCreatorConfigModel):
        self.output_type: FileType = generator_config.output_type
        self.output_folder: str = generator_config.output_folder
        self.output_name: str = generator_config.output_file_name
        self.output_trace_count: int = generator_config.output_trace_count
        self.output_sample_from: int = generator_config.output_sample_from
        self.output_sample_to: int = generator_config.output_sample_to
        self.output_trace_length: int = self.output_sample_to - self.output_sample_from
        self.output_parameters: ParameterWrapper = generator_config.output_parameters
        self.output_sample_coding: np.dtype = generator_config.output_sample_coding
        self.is_compressed: bool = generator_config.output_compressed
        self.data_output_path, self.output_path = self._get_output_paths()
        self.output_data, self.output_traces, self.output_traceset = self._create_output()
        self.is_output_numpy: bool = self.output_type == FileType.NPZ or self.output_type == FileType.NPY
        atexit.register(self.cleanup)
        self._perform_creator_checks()

    def register_cleanup(self) -> None:
        def handle_signal(signum, frame):
            print(f"Received signal {signum, frame}. Cleaning up...")
            self.cleanup()  # Explicitly call your cleanup method
            sys.exit(0)
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def cleanup(self):
        if self.output_traceset is not None:
            self.output_traceset.close()
        if self.output_data is not None:
            del self.output_data
            self.output_data = None
        if self.output_traces is not None:
            del self.output_traces
            self.output_traces = None

    def _perform_creator_checks(self):
        assert self.output_trace_count > 0, 'Trace count must be greater than 0'
        assert self.output_sample_from >= 0, 'Output trace start must be greater than or equal to 0'
        assert self.output_sample_to > self.output_sample_from, 'Invalid output interval'

    def _get_output_paths(self) -> Tuple[str, str]:
        os.makedirs(self.output_folder, exist_ok=True)
        joined_path: str = os.path.join(self.output_folder, self.output_name)
        match self.output_type:
            case FileType.TRS:
                return '', joined_path + '.trs'
            case FileType.NPZ:
                return '', joined_path + '.npz'
            case FileType.NPY:
                return joined_path + '_data.npy', joined_path + '_traces.npy'
            case _:
                raise Exception(f'Unsupported output type: {self.output_type.name}')

    def _create_output(self) -> Tuple[NDArray[np.uint8] | None, NDArray | None, TraceSet | None]:
        """
        Create output files and allocate memory for output data and traces
        """
        output_data: NDArray[np.uint8] | None = None
        output_traces: NDArray | None = None
        output_traceset: TraceSet | None = None
        print('Allocating files...', end='', flush=True)
        if self.output_type == FileType.NPY:
            output_data = np.lib.format.open_memmap(self.data_output_path, 'w+', 'uint8',
                                                    (self.output_trace_count, self.output_parameters.total_length))
            output_traces = np.lib.format.open_memmap(self.output_path, 'w+', self.output_sample_coding,
                                                      (self.output_trace_count, self.output_trace_length))
        elif self.output_type == FileType.NPZ:
            output_data = np.empty((self.output_trace_count, self.output_parameters.total_length), 'uint8')
            output_traces = np.empty((self.output_trace_count, self.output_trace_length),
                                          self.output_sample_coding)
        elif self.output_type == FileType.TRS:
            headers = {
                Header.TRS_VERSION: 2,
                Header.NUMBER_TRACES: 0,
                Header.NUMBER_SAMPLES: self.output_trace_length,
                Header.LENGTH_DATA: self.output_parameters.total_length,
                Header.DESCRIPTION: 'Generated traces',
                Header.SAMPLE_CODING: dtype_converter_map[self.output_sample_coding.name],
                Header.TRACE_PARAMETER_DEFINITIONS: self.output_parameters.generate_trs_parameters_definitions(),
            }
            output_traceset = trsfile.open(self.output_path, 'w', padding_mode=trsfile.TracePadding.AUTO,
                                                headers=headers, live_update=False)
        else:
            raise Exception(f'Unsupported output type: {self.output_type}')
        print('done', flush=True)
        return output_data, output_traces, output_traceset

    def save_output(self) -> None:
        print(f'Saving output to \"{self.output_path}\"...', end='', flush=True)
        if self.output_type == FileType.TRS:
            self.output_traceset.close()
            self.output_traceset = None # Prevent double free
        elif self.output_type == FileType.NPZ:
            if self.is_compressed:
                np.savez_compressed(self.output_path, traces=self.output_traces, data=self.output_data)
            else:
                np.savez(self.output_path, traces=self.output_traces, data=self.output_data)
        elif self.output_type == FileType.NPY:
            self.output_data.flush()
            self.output_traces.flush()
        else:
            raise Exception(f'Unsupported output type: {self.output_type}')
        print('done', flush=True)
