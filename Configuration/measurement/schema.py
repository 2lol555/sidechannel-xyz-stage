from dataclasses import dataclass, field

import numpy as np

from Common.Models.FileType import FileType
from Configuration.Models.Traces.TraceCreatorConfigModel import TraceCreatorConfigModel
from Helpers.ParameterWrapper import ParameterWrapper


@dataclass
class OutputConfig:
    output_file_name: str
    output_folder_path: str
    output_type: FileType
    output_parameters: ParameterWrapper
    trace_count: int
    sample_start: int
    sample_end: int
    sample_coding: np.dtype = np.dtype(np.int8)
    compressed: bool = False

    def to_trace_creator_config(self) -> TraceCreatorConfigModel:
        return TraceCreatorConfigModel(
            output_file_name=self.output_file_name,
            output_folder=self.output_folder_path,
            output_type=self.output_type,
            output_parameters=self.output_parameters,
            output_trace_count=self.trace_count,
            output_sample_from=self.sample_start,
            output_sample_to=self.sample_end,
            output_sample_coding=self.sample_coding,
            output_compressed=self.compressed,
        )


@dataclass
class PicoConfig:
    offset_mv: float
    timebase: int
    channel_a_range: int
    channel_b_range: int
    pre_trigger_samples: int
    trigger_channel: int
    trigger_threshold_adc: int
    trigger_direction: int
    trigger_delay: int = 0
    auto_trigger_ms: int = 0


@dataclass
class TargetConfig:
    key_length_bytes: int = 16
    fixed_nonce: bytes = field(default_factory=lambda: bytes(16))
    tvla_fixed_plaintext: bytes = field(default_factory=lambda: bytes.fromhex("DA39A3EE5E6B4B0D3255BFEF95601890"))
    ciphertext_timeout_ms: int = 250
    capture_start_delay_s: float = 0.05


@dataclass
class RuntimeConfig:
    ready_timeout_ms: int = 5000
    enable_picoscope: bool = True
    enable_chipwhisperer: bool = True


@dataclass
class MeasurementConfig:
    output: OutputConfig
    pico: PicoConfig
    target: TargetConfig
    runtime: RuntimeConfig
