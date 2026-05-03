import numpy as np
from dataclasses import dataclass
from Common.Models.FileType import FileType
from Helpers.ParameterWrapper import ParameterWrapper


@dataclass
class TraceCreatorConfigModel:
    output_file_name: str
    output_folder: str
    output_type: FileType
    output_parameters: ParameterWrapper
    output_trace_count: int = 1000
    output_sample_from: int = 0
    output_sample_to: int = -1
    output_sample_coding: np.dtype = np.dtype(np.int8)
    output_compressed: bool = False
