from dataclasses import dataclass
from Configuration.Models.Traces.ParallelWriterConfigModel import ParallelWriterConfigModel


@dataclass
class ResamplerConfigModel:
    parallel_config: ParallelWriterConfigModel
    window_size: int
    overlap: int
    resampler_step: int
    use_absolute_value: bool
    use_float: bool = True
    include_cut_in_output_name: bool = True

