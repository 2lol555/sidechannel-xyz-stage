from dataclasses import dataclass


@dataclass
class ApduPacket:
    instruction_class: int
    instruction: int
    optional_data_p1: int = 0x00
    optional_data_p2: int = 0x00
    data: list[int] | None = None
    expected_response_length: int = 0
