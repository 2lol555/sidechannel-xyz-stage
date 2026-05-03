import numpy as np
from numpy.typing import NDArray
from numba import njit, prange

class CorrelationCalculator:

    def __init__(self, attack_length: int, max_key: int):
        self.attack_sample_length: int = attack_length
        self.max_key: int = max_key
        self._index: int = 0
        self._traces_mean: NDArray = np.zeros(self.attack_sample_length, dtype=np.float64)
        self._predictions_mean: NDArray = np.zeros(self.max_key, dtype=np.float64)
        self._traces_variance: NDArray = np.zeros(self.attack_sample_length, dtype=np.float64)
        self._predictions_variance: NDArray = np.zeros(self.max_key, dtype=np.float64)
        self._covariance: NDArray = np.zeros((self.max_key, self.attack_sample_length), dtype=np.float64)

    @staticmethod
    @njit(parallel=True)
    def _update_cov(covariance: NDArray, prediction_variance: NDArray, traces_variance: NDArray, n_div: float) -> None:
        for i in prange(prediction_variance.shape[0]):
            prediction_variance[i] *= n_div
            for j in range(traces_variance.shape[0]):
                covariance[i, j] += prediction_variance[i] * traces_variance[j]

    @staticmethod
    @njit(parallel=False)
    def _update_statistics(mean: NDArray, variance: NDArray, data: NDArray, index: int) -> NDArray:
        delta_traces: NDArray = np.empty(data.shape[0], dtype=np.float64)
        for i in prange(data.shape[0]):
            delta_traces[i] = data[i] - mean[i]
            mean[i] += delta_traces[i] / index
            variance[i] += delta_traces[i] * (data[i] - mean[i])
        return delta_traces

    @staticmethod
    @njit(parallel=False)
    def _compute_incremental_correlation_jit(prev_cov: NDArray, prev_var_pred: NDArray,
                                             prev_var_traces: NDArray) -> NDArray:
        max_key: int = prev_var_pred.shape[0]
        attack_sample_length: int = prev_var_traces.shape[0]
        result: NDArray = np.empty((max_key, attack_sample_length), dtype=np.float64)
        for i in prange(max_key):
            sqrt_predictions: NDArray = np.sqrt(prev_var_pred[i])
            for j in range(attack_sample_length):
                sqrt_traces: NDArray = np.sqrt(prev_var_traces[j])
                denominator: NDArray = sqrt_predictions * sqrt_traces
                result[i, j] = prev_cov[i, j] / denominator if denominator != 0 else 0  # Avoid division by zero
        return result

    def add_trace_with_predictions(self, trace: NDArray, predictions: NDArray) -> None:
        self._index += 1
        n_div: float = (self._index - 1) / self._index
        delta_traces: NDArray = CorrelationCalculator._update_statistics(
            self._traces_mean, self._traces_variance, trace, self._index
        )
        delta_predictions: NDArray = CorrelationCalculator._update_statistics(
            self._predictions_mean, self._predictions_variance, predictions, self._index
        )
        CorrelationCalculator._update_cov(self._covariance, delta_predictions, delta_traces, n_div)

    def compute_incremental_correlation(self) -> NDArray:
        return CorrelationCalculator._compute_incremental_correlation_jit(
            self._covariance, self._predictions_variance, self._traces_variance
        )

    def reset(self) -> None:
        self._index = 0
        self._traces_mean.fill(0)
        self._predictions_mean.fill(0)
        self._covariance.fill(0)
        self._traces_variance.fill(0)
        self._predictions_variance.fill(0)

    @staticmethod
    def compute_correlation(traces: np.array, predictions: np.array) -> NDArray:
        """
        A faster correlation computation by taking the full matrix of predictions instead of just a column.
        This uses the two-pass algorithm for correlation calculation
        ref: https://github.com/ikizhvatov/efficient-columnwise-correlation
        """
        (trace_count, trace_length) = traces.shape  # n Traces of t samples
        (predictions_count, candidates) = predictions.shape  # n predictions for each of m candidates
        assert predictions_count == trace_count
        do = traces - (np.einsum('nt->t', traces, dtype='float64',
                                 optimize='optimal') / np.double(trace_count))  # compute O - mean(O)
        dp = predictions - (np.einsum('nm->m', predictions, dtype='float64',
                                      optimize='optimal') / np.double(trace_count)) # compute P - mean(P)
        numerator = np.einsum('nm,nt->mt', dp, do, optimize='optimal')
        temp1 = np.einsum('nm,nm->m', dp, dp, optimize='optimal')
        temp2 = np.einsum('nt,nt->t', do, do, optimize='optimal')
        temp = np.einsum('m,t->mt', temp1, temp2, optimize='optimal')
        denominator = np.sqrt(temp)
        return np.nan_to_num(numerator / denominator, posinf=0, nan=0)
