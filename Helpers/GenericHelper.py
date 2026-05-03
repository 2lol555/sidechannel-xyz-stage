import random
from Configuration.Constants import UINT_64, ASCON_SECTION_BIT_SIZE
from numba import njit

def hamming_weight(n: int):
    return bin(n).count('1')


def generate_random_number(limit: int = UINT_64) -> int:
    return random.randint(0, limit)


@njit
def get_bit_on_index_jit(number: int, index: int, length: int = ASCON_SECTION_BIT_SIZE) -> int:
    shift: int =  length - (index % length) - 1
    return number >> shift & 0x01


def get_bit_on_index(number: int, index: int, length: int = ASCON_SECTION_BIT_SIZE) -> int:
    shift: int =  length - (index % length) - 1
    return number >> shift & 0x01


def get_bits_on_interval(value: int, start: int, end: int,  length: int = ASCON_SECTION_BIT_SIZE) -> int:
    lsb_start = length - end
    lsb_end = length - start
    mask = (1 << (lsb_end - lsb_start)) - 1
    return (value >> lsb_start) & mask


def check_interval(start: int, end: int, length: int) -> None:
    assert start < end, f' Invalid interval {start} < {end}'
    assert start >= 0, 'Invalid start index (cannot be negative)'
    assert end <= length, f'Interval out of bounds of ({end} <= {length})'
