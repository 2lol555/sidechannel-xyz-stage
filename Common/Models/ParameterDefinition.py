from dataclasses import dataclass


@dataclass
class ParameterDefinition:
    name: str
    byte_length: int
