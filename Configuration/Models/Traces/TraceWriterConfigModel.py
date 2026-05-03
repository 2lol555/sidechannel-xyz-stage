from numpy import dtype
from dataclasses import dataclass
from Common.Models.FileType import FileType
from Common.Models.PathType import PathType
from Configuration.Models.Traces.TraceLoaderConfigModel import TraceLoaderConfigModel


@dataclass
class TraceWriterConfigModel:
    loader_config: TraceLoaderConfigModel
    path_type: PathType
    output_type: FileType
    output_folder: str = ''
    output_trace_length: int = 0
    output_trace_count: int = 0
    output_sample_coding: dtype | None = None
    output_compressed: bool = False
    divide_output_length_by: int = 1
