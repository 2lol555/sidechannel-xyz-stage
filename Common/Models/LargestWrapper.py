from dataclasses import dataclass


@dataclass
class LargestWrapper:
    largest_correlation: float = 0
    largest_index: int = 0
    second_largest_correlation: float = 0
    second_largest_index: int = 0
