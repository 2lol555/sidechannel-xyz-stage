from dataclasses import dataclass
from typing import List
from Configuration.Models.Traces.TraceCreatorConfigModel import TraceCreatorConfigModel


@dataclass
class TraceGenConfigModel:
    creator_config: TraceCreatorConfigModel
    random_distribution_mean: int
    random_distribution_std: int
    variable_noise: int
    leakage_position: int
    random_shift: int
    attack_register: int
    attack_register_from: int
    attack_register_to: int
    key: List[int]
    trace_gen_leakage_amplification: int = 1
