def calculate_output_length(config_length: int, input_length: int) -> int:
    match config_length:
        case 0:
            return input_length
        case x if x > 0:
            return config_length
        case _:
            return input_length - abs(config_length)


def calculate_config_length_interval(start: int | None = None, end: int | None = None) -> int:
    start = 0 if start is None else start
    assert start >= 0, 'Invalid start value'
    assert end is None or end > 0, 'Invalid end value'
    assert end is None or start < end, f'Invalid interval {start} - {end}'
    if end is None:
        return -start # How much should be subtracted from the input trace length
    else:
        return end - start # Length of the interval defined in config


def calculate_config_length_discard_set(discard_set: set) -> int:
    return -len(discard_set) # How much should be subtracted from the input trace count
