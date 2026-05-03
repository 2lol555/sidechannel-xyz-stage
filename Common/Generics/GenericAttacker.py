import math
import numpy as np
from numpy.typing import NDArray
from abc import abstractmethod, ABC
from typing import Set
from Common.AttackVisualization import show_attack_graph
from Common.AutomaticAlignment import AutomaticAlignment
from Common.ConditionalAverager import ConditionalAverager
from Common.CorrelationCalculator import CorrelationCalculator
from Common.Generics.GenericTraceLoader import GenericTraceLoader
from Common.Maps.TypeMaps import dtype_bits_count_map
from Common.Models.AttackResultWrapper import AttackResultWrapper
from Common.Models.FileType import FileType
from Common.Models.LargestWrapper import LargestWrapper
from Configuration.Models.Attack.GenericAttackConfigModel import GenericAttackConfigModel
from Configuration.Models.Tools.AutomaticAlignmentConfigModel import AutomaticAlignmentConfigModel
from Helpers.NumpyHelper import get_first_and_second_largest_index


class GenericAttacker(GenericTraceLoader, ABC):

    def __init__(self, config: GenericAttackConfigModel):
        print('Initializing attack objects...',)
        self.automatic_alignment: AutomaticAlignment | None = self._init_automatic_alignment(config.aa_config)
        max_trace_count = None
        if self.automatic_alignment is not None:
            max_trace_count, _ = self.automatic_alignment.initial_alignment()
        super().__init__(config.loader_config, max_trace_count)
        if max_trace_count is None:
            max_trace_count = self.trace_count
        # Init config
        self.evolution_step: int = config.evolution_step
        self.attacked_key_max: int = 2 ** config.attacked_key_bits
        self.data_max: int = 2 ** config.data_bit_length
        self.use_averager: bool = config.use_averager
        self.min_correlation: float = config.min_correlation
        self.min_correlation_difference: float = config.min_correlation_difference
        self.use_incremental_correlation: bool = config.use_incremental_correlation
        self.show_interactive_graph: bool = config.show_interactive_graph
        self.use_prediction_cache: bool = config.use_prediction_cache
        if config.attack_trace_count is None or config.attack_trace_count > max_trace_count:
            self.user_max_trace_count = max_trace_count
        else:
            self.user_max_trace_count = config.attack_trace_count
        # Current number of traces for the attack
        self.attack_trace_count = min(self.trace_count, self.user_max_trace_count)
        self.always_show_graph: bool = config.always_show_graph
        self.show_graph_attack_successful: bool = config.show_graph_attack_successful
        self._perform_attacker_checks()
        #Init intermediate arrays
        self._correlation_evol: NDArray = np.empty(
            (math.ceil(self.user_max_trace_count / config.evolution_step), self.attacked_key_max), dtype='float64'
        )
        self._conditional_averager: ConditionalAverager | None = None
        if self.use_averager:
            self._conditional_averager: ConditionalAverager = ConditionalAverager(
                self.attacked_key_max, config.attack_length
            )
        else:
            data_type: np.dtype = dtype_bits_count_map(config.data_bit_length)
            self._loaded_data: NDArray = np.empty(self.user_max_trace_count, data_type)
            self._loaded_traces = np.empty((self.user_max_trace_count, config.attack_length),
                                           dtype=self.sample_coding)
        if self.use_prediction_cache:
            self.predictions: NDArray = np.empty((self.data_max, self.attacked_key_max), config.prediction_dtype)
            self.observed_values: Set[int] | None = set()
        else:
            self.predictions = np.empty((self.user_max_trace_count, self.attacked_key_max), config.prediction_dtype)
            self.observed_values = None
        self._corr_calculator: CorrelationCalculator = CorrelationCalculator(config.attack_length, self.attacked_key_max)
        self._current_evol_step: int = 0
        # Used when auto alignment is enabled to correctly index samples in newly created files
        self._sample_shift: int = 0 if self.automatic_alignment is None else self.automatic_alignment.initial_start

    @staticmethod
    def _init_automatic_alignment(aa_configuration: AutomaticAlignmentConfigModel) -> AutomaticAlignment | None:
        automatic_alignment: AutomaticAlignment | None = None
        if aa_configuration is not None and aa_configuration.alignment_update_on >= 1:
            automatic_alignment = AutomaticAlignment(aa_configuration)
        return automatic_alignment

    def _perform_attacker_checks(self) -> None:
        assert self.user_max_trace_count > 0, 'Attacked traces need to be at least one trace'
        assert not (self.use_incremental_correlation and self.use_averager),\
            'Incremental correlation cannot be used together with averaging'

    def should_update_alignment(self, attack_sample_start: int) -> None:
        """
        Check if alignment should be updated before the next attack interval
        """
        if self.automatic_alignment is None:
            return
        alignment_performed: bool = self.automatic_alignment.check_automatic_alignment(attack_sample_start)
        if alignment_performed:
            self._sample_shift = attack_sample_start # Update sample shift for a new file
            self.reload_file()
            self.attack_trace_count = min(self.trace_count, self.user_max_trace_count)

    def add_trace(self, data: int, trace_idx: int, sample_start: int, sample_end: int,
                  predictions: NDArray) -> None:
        """
        Helper method that adds trace for processing on a specified index
        """
        if self.automatic_alignment is not None:
            # shift the current attack index to represent position in the current file
            sample_start -= self._sample_shift
            sample_end -= self._sample_shift
        if self.input_type == FileType.TRS:
            trace_samples: NDArray = self.traceset[trace_idx][sample_start:sample_end]
        elif self.is_input_numpy:
            trace_samples: NDArray = self.traces[trace_idx][sample_start:sample_end]
        else:
            raise Exception('Unsupported input type by generic attacker')
        if self.use_prediction_cache:
            if data not in self.observed_values:
                self.predictions[data] = predictions
                self.observed_values.add(data)
        else:
            self.predictions[trace_idx] = predictions
        if self.use_incremental_correlation:
            self._corr_calculator.add_trace_with_predictions(trace_samples, predictions)
            return
        if self.use_averager:
            self._conditional_averager.add_trace(data, trace_samples)
        else:
            self._loaded_data[trace_idx] = data
            self._loaded_traces[trace_idx] = trace_samples

    def compute_correlation(self, trace_idx: int) -> NDArray:
        """
        Compute correlation for a specified index and return correlation results
        """
        if self.use_incremental_correlation:
            return self._corr_calculator.compute_incremental_correlation()
        if self.use_averager:
            (data, traces) = self._conditional_averager.get_snapshot()
        else:
            data = self._loaded_data[:(trace_idx + 1)]
            traces = self._loaded_traces[:(trace_idx + 1)]
        if self.use_prediction_cache:
            predictions = self.predictions[data]
        else:
            predictions = self.predictions[:(trace_idx + 1)]
        return CorrelationCalculator.compute_correlation(traces, predictions)

    def update_evolution(self, trace_idx: int) -> NDArray:
        """
        Compute correlation update evolution graph data and return correlation results
        """
        correlation_results: NDArray = self.compute_correlation(trace_idx)
        self._correlation_evol[self._current_evol_step] = np.max(np.abs(correlation_results), axis=1)
        self._current_evol_step += 1
        return correlation_results

    def _is_attack_successful(self, correct_key: int, best_guesses: LargestWrapper) -> bool:
        key: int = best_guesses.largest_index # index is the value of the key
        if correct_key >= 0 and correct_key != key: # only when attacked key is known
            return False
        if best_guesses.largest_correlation < self.min_correlation:
            return False
        if best_guesses.largest_correlation < best_guesses.second_largest_correlation + self.min_correlation_difference:
            return False
        return True

    def evaluate_attack_stage(self, correlation_results: NDArray, graph_path: str = '',
                              correct_key: int = -1) -> AttackResultWrapper:
        """
        Evaluate attack after loading all traces and determine if the attack was successful
        """
        last_evolution_step: int = self._current_evol_step - 1
        best_guesses: LargestWrapper = get_first_and_second_largest_index(self._correlation_evol[last_evolution_step])
        attack_successful: bool = self._is_attack_successful(correct_key, best_guesses)
        current_key: int = best_guesses.largest_index
        if self.always_show_graph or (attack_successful and self.show_graph_attack_successful):
            if not attack_successful:
                graph_path = '' # Do not log graph when attack not successful
            show_attack_graph(correlation_results, self._correlation_evol[:self._current_evol_step],
                              self.evolution_step, correct_key, graph_path, self.show_interactive_graph)
        return AttackResultWrapper(attack_successful, current_key, best_guesses.largest_correlation)

    def is_index_graph_point(self, trace_idx: int) -> bool:
        """
        Calculate if this is index is represented in the graph using an evolution step or if it is an end of attack
        """
        return (trace_idx + 1) % self.evolution_step == 0 or (trace_idx + 1) == self.attack_trace_count

    def reset(self, hard: bool = False):
        if hard: # Hard reset is used when changing the attack target/stage
            if self.automatic_alignment is not None:
                self._sample_shift = self.automatic_alignment.initial_start
                self.automatic_alignment.reset()
        if self._conditional_averager is not None:
            self._conditional_averager.reset()
        if self.use_incremental_correlation:
            self._corr_calculator.reset()
        self._current_evol_step = 0

    # Prediction cache needs to be deleted when changing the attack target
    def delete_cache(self):
        if self.use_prediction_cache:
            self.predictions.fill(0)
            self.observed_values = None

    @abstractmethod
    def attack(self, attack_stage: int, sample_start: int, sample_end: int, graph_path: str) -> AttackResultWrapper:
        pass
