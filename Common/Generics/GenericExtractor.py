from abc import abstractmethod, ABC
from Common.Generics.GenericAttacker import GenericAttacker
from Common.Generics.GenericLogger import GenericLogger
from Common.Models.AttackResultWrapper import AttackResultWrapper
from Common.Models.AutomaticAlignmentCannotBePerformed import AutomaticAlignmentCannotBePerformed
from Configuration.Models.Extractors.GenericExtractorConfigModel import GenericExtractorConfigModel
from Configuration.ResamplerConfiguration import RESAMPLER_WINDOW_SIZE, RESAMPLER_OVERLAP, RESAMPLER_ABS


class GenericExtractor(GenericLogger, ABC):

    def __init__(self, attacker: GenericAttacker, config: GenericExtractorConfigModel):
        self._attacker: GenericAttacker = attacker
        self.attack_stage: int = config.attack_stage
        self.attack_start: int = config.attack_start
        self.attack_length: int = config.attack_length
        self.attack_step: int = config.attack_step
        self.attack_end = self._get_attack_end(config.attack_end)
        self.stop_on_first: bool = config.stop_on_first
        self.warning_traces_below: int = config.warning_traces_below
        super().__init__(config.logger_config)
        self._perform_extractor_checks()

    def _get_attack_end(self, attack_end: int) -> int:
        total_trace_length: int = self._attacker.trace_length
        if self._attacker.automatic_alignment is not None:
            # When using automatic alignment, the attacker is unaware of the total trace length
            total_trace_length = self._attacker.automatic_alignment.alignment.trace_length
        if attack_end > 0:
            return attack_end
        return total_trace_length

    def _perform_extractor_checks(self) -> None:
        assert self.attack_start >= 0, 'Attacked start cannot be negative'
        assert self.attack_start < self.attack_end, f'Invalid attack interval ({self.attack_start} < {self.attack_end})'
        if self._attacker.automatic_alignment is None: # Perform this check only if automatic alignment is not used
            assert self._attacker.trace_length >= self.attack_end, (f'File contains not enough samples in:'
                f'{self._attacker.target_path}, need: {self._attacker.attack_trace_count}, '
                f'contains: {self._attacker.trace_count}')
        else:
            assert self.attack_start == self._attacker.automatic_alignment.initial_start,\
                (f'Auto alignment must have same start {self.attack_start} vs'
                 f' {self._attacker.automatic_alignment.initial_start}')
            assert self.attack_length == self._attacker.automatic_alignment.attack_length,\
                (f'Auto alignment must have same attack length {self.attack_length} vs'
                 f' {self._attacker.automatic_alignment.attack_length}')
            assert self.attack_step == self._attacker.automatic_alignment.attack_step,\
                (f'Auto alignment must have same overlap {self.attack_step} vs'
                 f' {self._attacker.automatic_alignment.attack_step}')
            assert self.attack_end == self._attacker.automatic_alignment.attack_end,\
                f'Auto alignment must have same end {self.attack_end} vs {self._attacker.automatic_alignment.attack_end}'
        assert self.attack_length > 0, 'Attacked length must be greater than 0'
        assert self.attack_step >= 0, 'Attacked overlap cannot be negative'

    def get_current_resampling(self) -> str:
        if self.log_resampler_config:
            if self._attacker.automatic_alignment is not None:
                resampling_length: int = self._attacker.automatic_alignment.alignment.alignment_resampling_length
                resampling_abs: bool = self._attacker.automatic_alignment.alignment.alignment_resampling_abs
                if resampling_length > 0:
                    resampler_abs_message: str = 'AWR' if resampling_abs else 'WR'
                    resampling_message: str = f'{resampler_abs_message}({resampling_length}/{1})'
                    return resampling_message
            resampler_abs_message: str = 'AWR' if RESAMPLER_ABS else 'WR'
            resampling_message: str = f'{resampler_abs_message}({RESAMPLER_WINDOW_SIZE}/{RESAMPLER_OVERLAP})'
        else:
            resampling_message = 'Not used'
        return resampling_message

    @abstractmethod
    def perform_result_operation(self, result: AttackResultWrapper, attack_sample_start: int,
                                 attack_sample_end: int, attack_stage: int) -> None:
        """
            Perform operation specific for the attack
        """
        pass

    def extract_specific_stage(self, attack_stage: int) -> None:
        attack_end_interval: int =  self.attack_end - self.attack_length + 1 # Prevents out-of-bounds read
        for attack_sample_start in range(self.attack_start, attack_end_interval, self.attack_step):
            attack_sample_end: int = attack_sample_start + self.attack_length
            current_graph_path: str = self.get_current_graph_path(attack_sample_start, attack_sample_end, attack_stage)
            try:
                current_result: AttackResultWrapper = self._attacker.attack(
                    attack_stage, attack_sample_start, attack_sample_end, current_graph_path
                )
            except AutomaticAlignmentCannotBePerformed as ex:
                print(ex)
                break
            self.perform_result_operation(current_result, attack_sample_start, attack_sample_end, attack_stage)
            if current_result.success:
                self.log_success_message(attack_stage, attack_sample_start, attack_sample_end,
                                         current_result.correlation)
                if self.stop_on_first:
                    break
            if (self.warning_traces_below > 0 and self._attacker.attack_trace_count < self.warning_traces_below and
                    self._attacker.automatic_alignment is not None and
                    self._attacker.automatic_alignment.alignment.threshold > 0):
                self.log_aa_warning_message(attack_stage, attack_sample_start, attack_sample_end,
                                            self._attacker.attack_trace_count, self._attacker.max_trace_count)
            self._attacker.reset()
        self._attacker.reset(hard=True)  # Reset alignment shift and automatic alignment if activated

    def extract_key(self, stage_count: int, stage_step: int = 1) -> None:
        if self.attack_stage < 0:
            attack_stages = range(0, stage_count, stage_step)
        else:
            attack_stages = [self.attack_stage]
        for attack_stage in attack_stages:
            self.extract_specific_stage(attack_stage)
