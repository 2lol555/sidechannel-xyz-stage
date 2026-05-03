from dataclasses import dataclass
from Configuration.Models.Traces.ParallelWriterConfigModel import ParallelWriterConfigModel

@dataclass
class AlignmentConfigModel:
    parallel_writer_config: ParallelWriterConfigModel
    max_shift: int
    alignment_resampling_length: int = 0
    alignment_resampling_abs: bool = False
    threshold: float = 0
    reference_index: int = 0
    alignment_log_enable: bool = False
    show_graph: bool = False
    graph_trace_count: int = 4
    graph_trace_length: int = 5000
    dry_run: bool = False
    include_cut: bool = False