from dataclasses import dataclass
from Configuration.Models.Traces.TraceWriterConfigModel import TraceWriterConfigModel


@dataclass
class ParallelWriterConfigModel:
    writer_config: TraceWriterConfigModel
    process_count: int
    data_shm_name: str
    traces_shm_name: str
