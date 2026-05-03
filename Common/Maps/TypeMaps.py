import numpy as np
from trsfile import SampleCoding


dtype_converter_map: dict[str, SampleCoding] = {
    'int8': SampleCoding.BYTE,
    'int16': SampleCoding.SHORT,
    'int32': SampleCoding.INT,
    'uint8': SampleCoding.BYTE,
    'uint16': SampleCoding.SHORT,
    'uint32': SampleCoding.INT,
    'float32': SampleCoding.FLOAT,
    'float64': SampleCoding.FLOAT,
}


def dtype_bits_count_map(data_bit_count: int) -> np.dtype:
    if data_bit_count < 8:
        return np.dtype(np.uint8)
    elif data_bit_count < 16:
        return np.dtype(np.uint16)
    elif data_bit_count < 32:
        return np.dtype(np.uint32)
    elif data_bit_count < 64:
        return np.dtype(np.uint64)
    else:
        raise Exception('Unsupported data bit count')
