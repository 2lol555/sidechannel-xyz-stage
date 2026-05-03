import sys
import numpy as np
from numpy.typing import NDArray
from os.path import getsize
from Common.Models.LargestWrapper import LargestWrapper
from Configuration.Constants import NUMPY_HEADER_LENGTH


def get_first_and_second_largest_index(numpy_array: NDArray) -> LargestWrapper:
    largest_value: float = float('-inf')
    largest_index: int = -1
    second_largest_value: float = float('-inf')
    second_largest_index: int = -1
    for index in range(len(numpy_array)):
        current_value: float =  abs(float(numpy_array[index])) # the correlation may be positive or negative
        if current_value >= largest_value:
            second_largest_value = largest_value
            second_largest_index = largest_index
            largest_value = current_value
            largest_index = index
        elif current_value >= second_largest_value:
            second_largest_value = current_value
            second_largest_index = index
    return LargestWrapper(largest_value, largest_index, second_largest_value, second_largest_index)


def remove_rows_numpy(filename: str, original_row_count: int, discarded_row_count: int, row_length: int) -> None:
    file_size: int = getsize(filename)
    with open(filename, 'r+', encoding='latin1') as npy_mem_file:
        line: str = npy_mem_file.readline()
        line = line.strip()
        line = line.replace(f"'shape': ({original_row_count},",
                            f"'shape': ({original_row_count - discarded_row_count},")
        new_line_length: int = len(line)
        line = line + ' ' * (NUMPY_HEADER_LENGTH - new_line_length - 1) + '\n'
        npy_mem_file.seek(0)
        npy_mem_file.write(line)
        npy_mem_file.truncate(file_size - discarded_row_count * row_length)


def convert_big_endian_bytes_to_numpy(bytes_big_endian: bytes) -> NDArray:
    # Numba only supports platform endianity, we need to correctly convert it
    array_64_bit: NDArray = np.frombuffer(bytes_big_endian, dtype='>u8')  # Big-endian 64-bit dtype
    platform_endian: str = sys.byteorder
    if platform_endian == 'little':
        return array_64_bit.byteswap().view(array_64_bit.dtype.newbyteorder())  # Convert to native endianity
    return array_64_bit


def convert_to_hex_string(raw_data: NDArray) -> str:
    return '0x' + raw_data.tobytes().hex().upper()
