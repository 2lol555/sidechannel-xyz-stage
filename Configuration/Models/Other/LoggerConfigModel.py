from dataclasses import dataclass


@dataclass
class LoggerConfigModel:
    log_success_attempts: bool
    log_folder_path: str
    log_resampler_config: bool
    log_include_graphs: bool
    print_log: bool = True
