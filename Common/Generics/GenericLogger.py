import atexit
import os
import sys
import signal
from abc import abstractmethod, ABC
from datetime import datetime
from typing import Tuple, TextIO
from Configuration.Models.Other.LoggerConfigModel import LoggerConfigModel


class GenericLogger(ABC):

    def __init__(self, config: LoggerConfigModel):
        self.log_success_attempts: bool = config.log_success_attempts
        self.log_folder_path: str = config.log_folder_path
        self.log_resampler_config: bool = config.log_resampler_config
        self.log_include_graphs: bool = config.log_include_graphs
        self.log_path, self.graph_path = self._prepare_logging()
        self._log_file: TextIO | None = open(self.log_path, 'a') if self.log_success_attempts else None
        atexit.register(self.cleanup)
        self.print_log = config.print_log

    def register_cleanup(self) -> None:
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
        signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    def cleanup(self) -> None:
        if self._log_file is not None:
            self._log_file.close()

    def _prepare_logging(self) -> Tuple[str, str]:
        log_path: str = ''
        graph_path: str = ''
        if self.log_success_attempts:
            current_datetime: str = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
            folder_path: str = self.log_folder_path
            log_path = current_datetime + '.log'
            if self.log_include_graphs:
                folder_path = os.path.join(folder_path, 'log_folder_' + current_datetime + '')
                graph_path = os.path.join(folder_path, 'graph')
            log_path = os.path.join(folder_path, log_path)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        return log_path, graph_path

    @abstractmethod
    def get_log_message(self, attack_stage: int, attack_sample_start: int, attack_sample_end: int,
                        correlation: float) -> str:
        pass

    def get_current_graph_path(self, start: int, end: int, attack_stage: int) -> str:
        if self.graph_path != '':
            return self.graph_path + f'_{attack_stage}_{start}-{end}.png'
        return ''

    def log_success_message(self, attack_stage: int, attack_sample_start: int, attack_sample_end: int,
                            correlation: float) -> None:
        if not self.print_log and self._log_file is None:
            return
        message: str = self.get_log_message(attack_stage, attack_sample_start, attack_sample_end, correlation)
        if self._log_file is not None:
            self._log_file.write(message)
        if self.print_log:
            print(f'Successful attack: {message}')
        return

    def log_aa_warning_message(self, attack_stage: int, attack_sample_start: int, attack_sample_end: int,
                               current_trace_count: int, max_trace_count: int) -> None:
        if not self.print_log and self._log_file is None:
            return
        message: str = f'Warning: When attacking stage {attack_stage} on {attack_sample_start}-{attack_sample_end}, '\
                       f'too many traces discarded by automatic alignment. {max_trace_count} -> {current_trace_count}\n'
        if self._log_file is not None:
            self._log_file.write(message)
        if self.print_log:
            print(message)
        return
