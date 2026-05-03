from dataclasses import dataclass


@dataclass
class AttackResultWrapper:
    success: bool
    key: int
    correlation: float
