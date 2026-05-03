import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from trsfile import TraceSet
from Common.Models.FileType import FileType


def show_alignment_graph(traceset: TraceSet | None, traces: NDArray, new_trace_count: int,
                         reference_index: int, graph_count: int, graph_size: int, output_type: FileType) -> None:
    #Generate ten random indexes to show in the graph
    if new_trace_count == 0:
        print('No traces to show, skipping graph generation')
        return
    rand_array: NDArray = np.random.randint(0, new_trace_count, size=graph_count)
    print('Traces used in the graph:', rand_array)
    print('Generating graph...', end='', flush=True)
    for trace_idx in range(graph_count):
        if output_type == FileType.TRS:
            plt.plot(traceset[rand_array[trace_idx]].samples[:graph_size], color='gray')
        else:
            plt.plot(traces[rand_array[trace_idx]][:graph_size], color='gray')
    if output_type == FileType.TRS:
        plt.plot(traceset[reference_index].samples[:graph_size], color='red')
    else:
        plt.plot(traces[reference_index][:graph_size], color='red')
    plt.show()
    print('done', flush=True)
