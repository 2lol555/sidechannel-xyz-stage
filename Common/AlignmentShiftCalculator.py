import numpy as np
from numpy.typing import NDArray
from scipy.fftpack import fft, ifft, fftshift


#Use fft to compute the normalized cross-correlation between a template x and a trace y.
def normalized_cross_correlation_using_fft(ref, trace) -> NDArray:
    ref: NDArray = ref - np.average(ref) / np.std(ref)
    trace: NDArray = trace - np.average(trace) / np.std(trace)
    fft_ref: NDArray = fft(ref)
    fft_trace: NDArray = fft(np.flipud(trace))
    cross_correlation: NDArray = np.real(ifft(fft_ref * fft_trace))

    #normalize the output
    trace_sum: NDArray = np.sum(trace)
    trace_sum_squared: NDArray = np.sum(np.square(trace))
    sigma_a: NDArray = np.sqrt(trace_sum_squared - (trace_sum ** 2) / len(ref))
    sigma_t: NDArray = np.std(ref) * np.sqrt(len(ref) - 1)
    normalized_cross_correlation: NDArray = (cross_correlation - trace_sum * np.mean(ref)) / (sigma_t * sigma_a)
    return fftshift(normalized_cross_correlation)


# Computes the normalized cross-correlation between two misaligned Traces and outputs the best shift between them.
def compute_shift(ref: NDArray, trace: NDArray, start: int = 0, end: int = None,
                  max_shift: int = None) -> tuple[int, float]:
    if end is None:
        end = len(trace)
    pad: int = end-start
    if max_shift is None:
        ref_x: NDArray = np.pad(ref[start:end], (start+pad,len(trace)-end+pad),'constant',constant_values=0)
        trace_y: NDArray = np.pad(trace, (pad,),'constant',constant_values=0)
    else:
        ref_x = np.pad(ref[start:end], (max_shift + pad),'constant',constant_values=0)
        trace_y = np.pad(trace[start-max_shift:end+max_shift], (pad,),'constant',constant_values=0)
    assert len(ref_x) == len(trace_y)
    correlations: NDArray[float] = normalized_cross_correlation_using_fft(ref_x,trace_y)
    assert len(correlations) == len(ref_x)
    zero_index: int = round(len(ref_x) / 2) - 1
    if max_shift is not None:
        assert max_shift <= zero_index
        correlations = correlations[zero_index-max_shift:zero_index+max_shift + 1]
        zero_index = max_shift
    shift: int = np.argmax(correlations) - zero_index
    return shift, correlations.max()


# Computes only with already gathered relevant data (optimization reasons)
def compute_shift_cut(ref: NDArray, trace: NDArray, max_shift: int) -> tuple[int, float]:
    assert len(ref) + 2 * max_shift == len(trace)
    pad: int = len(ref)
    ref_x: NDArray = np.pad(ref, (max_shift + pad), 'constant', constant_values=0)
    trace_y: NDArray = np.pad(trace, (pad,), 'constant', constant_values=0)
    correlations: NDArray[float] = normalized_cross_correlation_using_fft(ref_x, trace_y)
    assert len(correlations) == len(ref_x)
    zero_index: int = round(len(ref_x) / 2) - 1
    assert max_shift <= zero_index
    correlations = correlations[zero_index - max_shift:zero_index + max_shift + 1]
    shift: int = np.argmax(correlations) - max_shift
    return shift, correlations.max()
