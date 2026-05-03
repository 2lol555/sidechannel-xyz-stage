import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from matplotlib.pyplot import Axes
from Configuration.Constants import GRAPH_FONT_SIZE
from Helpers.VisualizationHelper import show_non_interactive_image


def show_attack_graph(correlation_values: NDArray, correlation_evol: NDArray, evolution_step: int,
                      correct_key: int = -1, graph_save_path: str = '', show_interactive_graph: bool = False,
                      fontsize: int = GRAPH_FONT_SIZE) -> None:
    print('Generating graph...', end='', flush=True)
    cpa_plot: Axes = plt.subplot2grid((2, 2), (0, 0), colspan=2)
    evol_plot: Axes  = plt.subplot2grid((2, 2), (1, 0))
    correct_pos_plot: Axes  = plt.subplot2grid((2, 2), (1, 1))
    render_cpa_graph(cpa_plot, correlation_values, correct_key, fontsize)
    correlation_evol_transposed: NDArray = correlation_evol.T
    render_evol_graph(evol_plot, correlation_evol_transposed, evolution_step, correct_key, fontsize)
    render_position_plot(correct_pos_plot, correlation_evol_transposed, evolution_step, correct_key, fontsize)
    plt.tight_layout()
    if graph_save_path != '': # Log graphs if a path not empty
        plt.savefig(graph_save_path)
    if show_interactive_graph:
        plt.show()
    else:
        show_non_interactive_image()
    plt.close()
    print('done', flush=True)


def render_cpa_graph(cpa_plot: Axes, correlation_values: NDArray, correct_key: int, fontsize: int) -> None:
    max_key: int = correlation_values.shape[0]
    sample_count: int = correlation_values.shape[1]
    cpa_x: range = range(sample_count)
    for i in range(max_key):
        cpa_plot.plot(range(sample_count), correlation_values[i], color='blue')
    if correct_key >= 0: # Only if correct is known
        cpa_plot.plot(cpa_x, correlation_values[correct_key], color='red')
    cpa_plot.set_ylabel('Correlation', fontsize=fontsize)
    cpa_plot.set_xlabel('Time(sample)', fontsize=fontsize)


def render_evol_graph(evol_plot: Axes, correlation_evol: NDArray, evolution_step: int, correct_key: int,
                      fontsize: int) -> None:
    max_key: int = correlation_evol.shape[0]
    original_trace_count: int = correlation_evol.shape[1] * evolution_step
    evol_x: range = range(0, original_trace_count, evolution_step)
    for i in range(max_key):
        evol_plot.plot(evol_x, correlation_evol[i], color='gray')
    if correct_key >= 0: # Only if correct is known
        evol_plot.plot(evol_x, correlation_evol[correct_key], color='red')
    evol_plot.set_ylabel('Correlation', fontsize=fontsize)
    evol_plot.set_xlabel('Number of Traces', fontsize=fontsize)


def render_position_plot(correct_pos_plot: Axes, correlation_evol: NDArray, evolution_step: int,
                         correct_key: int, fontsize: int) -> None:
    arg_max: NDArray = np.argsort(np.argsort(-correlation_evol, axis=0), axis=0)
    original_trace_count: int = correlation_evol.shape[1] * evolution_step
    corr_position_x: range = range(0, original_trace_count, evolution_step)
    if correct_key >= 0: # Only if the correct key is known
        correct_pos_plot.plot(corr_position_x, arg_max[correct_key], color='gray')
    correct_pos_plot.set_ylabel('Correct key candidate rank', fontsize=fontsize)
    correct_pos_plot.set_xlabel('Number of Traces', fontsize=fontsize)
