import numpy as np
from numpy.typing import NDArray
from Common.Models.ParameterDefinition import ParameterDefinition
from trsfile.parametermap import TraceParameterDefinitionMap
from trsfile.traceparameter import ParameterType, TraceParameterDefinition
from Helpers.NumpyHelper import convert_to_hex_string


class ParameterWrapper:

    def __init__(self, parameters: list[ParameterDefinition]):
        self.parameters = parameters
        self.total_length = self._get_parameters_total_length()
        self.parameter_intervals = self._get_parameters_interval()

    def _get_parameters_total_length(self) -> int:
        return sum(item.byte_length for item in self.parameters)

    def _get_parameters_interval(self) -> dict[str, tuple[int, int]]:
        parameter_start: int = 0
        parameter_intervals: dict[str, tuple[int, int]] = {}
        for parameter in self.parameters:
            parameter_intervals[parameter.name] = (parameter_start, parameter_start + parameter.byte_length)
            parameter_start += parameter.byte_length
        return parameter_intervals

    def get_parameter_byte(self, array: NDArray[np.uint8], parameter_name: str,  byte_index: int) -> int:
        start, end = self.parameter_intervals.get(parameter_name)
        length = end - start
        if length < byte_index:
            raise IndexError(f'Byte index {byte_index} is out of range for parameter {parameter_name}')
        return int(array[start + byte_index])

    def get_parameter(self, array: NDArray[np.uint8], parameter_name: str) -> NDArray[np.uint8]:
        start, end = self.parameter_intervals.get(parameter_name)
        return array[start:end]

    def print_parameters(self, data: NDArray[np.uint8], show_hex: bool = False) -> None:
        for parameter in self.parameters:
            start, end = self.parameter_intervals.get(parameter.name)
            data_segment: NDArray = data[start:end]
            if show_hex:
                data_segment_str: str = convert_to_hex_string(data_segment)
            else:
                data_segment_str: str = str(data_segment)
            print(f'{parameter.name}: {data_segment_str}')
        print() # Add additional new line on the end of print

    def write_parameter_to_array(self, array: NDArray[np.uint8], parameter_name: str,
                                 parameter_value: NDArray[np.uint8]) -> None:
        start, end = self.parameter_intervals.get(parameter_name)
        assert parameter_value.nbytes == end - start, 'Parameter length does not match'
        array[start:end] = parameter_value

    def generate_trs_parameters_definitions(self) -> TraceParameterDefinitionMap:
        parameter_definition: dict[str, TraceParameterDefinition] = {}
        parameter_start: int = 0
        for parameter in self.parameters:
            parameter_definition[parameter.name] = TraceParameterDefinition(ParameterType.BYTE, parameter.byte_length,
                                                                            parameter_start)
            parameter_start += parameter.byte_length
        return TraceParameterDefinitionMap(parameter_definition)
