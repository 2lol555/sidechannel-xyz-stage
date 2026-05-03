from typing import Tuple
from AttackTools.Alignment import Alignment
from Common.Models.AutomaticAlignmentCannotBePerformed import AutomaticAlignmentCannotBePerformed
from Configuration.Models.Tools.AutomaticAlignmentConfigModel import AutomaticAlignmentConfigModel


class AutomaticAlignment:

    def __init__(self, aa_config: AutomaticAlignmentConfigModel) -> None:
        self.alignment: Alignment = Alignment(aa_config.alignment_configuration)
        self.initial_start: int = aa_config.attack_start
        self.attack_length: int = aa_config.attack_length
        self.attack_step: int = aa_config.attack_step
        self.attack_end: int = aa_config.attack_end if aa_config.attack_end > 0 else self.alignment.trace_length
        self.alignment_from_center: int = aa_config.alignment_interval_length // 2
        self.alignment_update_on: int = aa_config.alignment_update_on
        self.automatic_alignment_length = self.attack_length + (aa_config.alignment_update_on - 1) * self.attack_step
        self.alignment_interval_center: int = round(self.automatic_alignment_length / 2)
        self._alignment_counter: int = 0
        self._just_initialized: bool = False
        self._perform_checks()

    def _perform_checks(self):
        assert self.alignment_update_on > 0, ' Invalid alignment update on (must be greater than 0)'
        assert self.alignment.trace_length >= self.attack_end,\
            f'Attack end is out of bounds ({self.alignment.trace_length} >= {self.attack_end})'

    def _perform_alignment(self, attack_start: int) -> Tuple[int, int]:
        alignment_center: int = attack_start + self.alignment_interval_center
        alignment_start: int = alignment_center - self.alignment_from_center
        alignment_end: int = alignment_center + self.alignment_from_center
        attack_end_before_next_alignment: int = attack_start + self.automatic_alignment_length
        print(f'\nRunning automatic alignment on {alignment_start} - {alignment_end}...', )
        return self.alignment.run_alignment(alignment_start, alignment_end, attack_start,
                                            attack_end_before_next_alignment)

    def _check_bounds(self, attack_sample_start: int) -> None:
        alignment_end: int = attack_sample_start + self.alignment_interval_center + self.alignment_from_center
        if alignment_end <= self.alignment.trace_length:
            return
        raise AutomaticAlignmentCannotBePerformed(f'Automatic alignment interval out of bounds on {attack_sample_start}'
                                                  f', alignment_end: {alignment_end} > {self.alignment.trace_length}.')

    def initial_alignment(self) -> Tuple[int, int]:
        print('Starting initial automatic alignment...')
        self._just_initialized = True
        return self._perform_alignment(self.initial_start)

    # Check if automatic alignment should be performed if yes, perform it and returns True, otherwise False
    def check_automatic_alignment(self, attack_sample_start: int) -> bool:
        if self._just_initialized: # Prevent updating alignment two times after initialization
            self._just_initialized = False
            return False
        self._alignment_counter += 1
        if self._alignment_counter % self.alignment_update_on != 0:
            return False
        self._check_bounds(attack_sample_start)
        self._perform_alignment(attack_sample_start)
        return True

    def reset(self) -> None:
        self._alignment_counter = -1 # Make the first iteration to align the traces
