from dataclasses import dataclass
from Configuration.Models.Tools.AlignmentConfigModel import AlignmentConfigModel


@dataclass
class AutomaticAlignmentConfigModel:
    alignment_configuration: AlignmentConfigModel
    attack_start: int
    attack_length: int
    attack_step: int
    attack_end: int
    alignment_update_on: int
    alignment_interval_length: int
