import numpy as np

# Global Constants
UINT_64: int = 2**64 # Maximum unsigned 64 bit value
NUMPY_HEADER_LENGTH: int = 128
TRACES_NAME: str = 'traces'
DATA_NAME: str = 'data'
KEY_NAME: str = 'KEY'
PLAIN_TEXT_NAME: str = 'PT'
NONCE_NAME: str = 'NONCE'

KEY_BIT_NAME: str = 'key-bit'
KEY_BYTE_NAME: str = 'key'
CONFIDENCE_NAME: str = 'confidence'
START_NAME: str = 'start'
END_NAME: str = 'end'
GRAPH_FONT_SIZE: int = 10
INT_LOW: int = -128
INT_HIGH: int = 127

# Type constants
ASCON_KEY_WITH_CONFIDENCE_DTYPE: np.dtype = np.dtype([(KEY_BIT_NAME, np.bool_), (CONFIDENCE_NAME, np.float32),
                                                      (START_NAME, np.uint32), (END_NAME, np.uint32)])
AES_KEY_WITH_CONFIDENCE_DTYPE: np.dtype = np.dtype([(KEY_BYTE_NAME, np.uint8), (CONFIDENCE_NAME, np.float32),
                                                    (START_NAME, np.uint32), (END_NAME, np.uint32)])

# Postfix constants
POSTFIX_FOR_DATA: str = "_data"
POSTFIX_FOR_TRACES: str = "_traces"

# Alignment constants
ALIGNMENT_SHM_NAME_REF: str = 'alignment_ref'
ALIGNMENT_SHM_NAME_TRACES: str = 'alignment_traces_output'
ALIGNMENT_SHM_NAME_DATA: str = 'alignment_data_output'
ADVANCED_ALIGNMENT_STEP: int = 1

#Converter constants
CONVERTER_SHARE_MEMORY_NAME_TRACES: str = 'converter_traces_output'
CONVERTER_SHARE_MEMORY_NAME_DATA: str = 'converter_data_output'

# Resampler constants
RESAMPLER_SHARE_MEMORY_NAME_TRACES: str = 'resampler_traces_output'
RESAMPLER_SHARE_MEMORY_NAME_DATA: str = 'resampler_data_output'


# Ascon Constants
ASCON_SECTION_BIT_SIZE: int = 64
ASCON_SECTION_BYTE_SIZE: int = 8
ASCON_SECTION_COUNT: int = 5
BYTE_BIT_LEN: int = 8
NONCE_SECTION_LEN: int = 9
ASCON_DATA_START: int = 32
ASCON_IV: int = 0x80400C0600000000
ASCON_KEY_SIZE: int = 2 # in 64-bit chunks
ASCON_KEY_BYTE_SIZE: int = 16
ASCON_NONCE_BYTE_SIZE: int = 16
ASCON_NONCE_POSITION: int = 3
ASCON_ATTACKED_BITS: int = 3 # Number of key bits attacked by one bit of intermediate state
ASCON_NONCE_BITS: int = 6 # Number of nonces used during attack on one bit of intermediate state
ASCON_PT_SIZE: int = 2 # in 64-bit chunks
ASCON_NONCE_SIZE: int = 2 # in 64-bit chunks
ASCON_KEY_SIZE_BITS: int = ASCON_KEY_SIZE * ASCON_SECTION_BIT_SIZE
ASCON_ROUND_CONSTANT_BITS: list[int] = list(range(56,60))
ASCON_FIRST_ROUND_CONSTANT: int = 0xF0

# Aes constants

AES_KEY_SIZE: int = 16 # in bytes
AES_INTERMEDIATE_COMBINATIONS: int = 256
