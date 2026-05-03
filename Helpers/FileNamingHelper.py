import os
from os.path import splitext
from typing import Tuple
from Common.Models.FileType import FileType
from Configuration.AlignmentConfiguration import ALIGNMENT_OUTPUT_COMPRESSED
from Configuration.Constants import POSTFIX_FOR_TRACES, POSTFIX_FOR_DATA
from Configuration.ResamplerConfiguration import RESAMPLER_ABS, RESAMPLER_WINDOW_SIZE, RESAMPLER_OVERLAP


def get_resampler_output_paths(traces_input_path: str, output_type: FileType, output_folder: str = '',
                               cut_from: int = 0, cut_to: int = 0, include_cut: bool = False) -> Tuple[str, str]:
    output_location: str = get_output_folder(traces_input_path, output_folder)
    path_addition: str = get_cut_addition(cut_from, cut_to, include_cut)
    if RESAMPLER_ABS:
        path_addition += f'+AWR({RESAMPLER_WINDOW_SIZE},{RESAMPLER_OVERLAP})'
    else:
        path_addition += f'+WR({RESAMPLER_WINDOW_SIZE},{RESAMPLER_OVERLAP})'
    return get_output_paths(output_location, output_type, path_addition)


def get_alignment_output_paths(traces_input_path: str, output_type: FileType, output_folder: str = '',
                               cut_from: int = 0, cut_to: int = 0, include_cut: bool = False) -> Tuple[str, str]:
    output_location: str = get_output_folder(traces_input_path, output_folder)
    path_addition: str = get_cut_addition(cut_from, cut_to, include_cut) + '_align'
    if output_type == FileType.NPZ and ALIGNMENT_OUTPUT_COMPRESSED:
        path_addition += '_compressed'
    return get_output_paths(output_location, output_type, path_addition)


def get_converter_output_paths(traces_input_path: str, output_type: FileType, output_folder: str = '',
                               cut_from: int = 0, cut_to: int = 0, include_cut: bool = False) -> Tuple[str, str]:
    output_location: str = get_output_folder(traces_input_path, output_folder)
    path_addition: str = get_cut_addition(cut_from, cut_to, include_cut) + '_conv'
    return get_output_paths(output_location, output_type, path_addition)


def get_output_folder(traces_input_path: str, output_folder: str = '') -> str:
    if output_folder == '':
        return remove_extension_with_postfix(traces_input_path, POSTFIX_FOR_TRACES)
    else:
        input_path_without_extension: str = remove_extension_with_postfix(traces_input_path, POSTFIX_FOR_TRACES)
        input_file_name: str = input_path_without_extension.split(os.sep)[-1]
        if output_folder[-1] != os.sep:
            output_folder += os.sep
        return output_folder + input_file_name


def get_cut_addition(cut_from: int, cut_to: int, include_cut: bool) -> str:
    path_addition: str = ''
    if include_cut and cut_to > 0:
        start_addition: str = get_shorten_number_str(cut_from)
        end_addition: str = get_shorten_number_str(cut_to)
        path_addition: str = f'_cut({start_addition}-{end_addition})'
    return path_addition


def get_shorten_number_str(number: int) -> str:
    if number > 1000000:
        return format(number / 1000000, ".1f") + 'm'
    elif number > 1000:
        return format(number / 1000, ".1f") + 'k'
    else:
        return str(number)


def get_output_paths(output_location: str, output_type: FileType, path_addition: str) -> Tuple[str, str]:
    output_location += path_addition
    return add_correct_extension(output_location, output_type)


def remove_extension_with_postfix(input_path: str, postfix: str) -> str:
    if input_path == '':
        return ''
    reduced_input_path = splitext(input_path)[0]
    postfix_length = len(postfix)
    if len(reduced_input_path) > postfix_length and \
        reduced_input_path[-postfix_length:] == postfix:
        reduced_input_path = reduced_input_path[:-postfix_length]
        return reduced_input_path
    return reduced_input_path


def add_correct_extension(output_path: str, output_type: FileType) -> Tuple[str, str]:
    data_output_location: str = ''
    match output_type:
        case FileType.NPY:
            data_output_location = output_path + POSTFIX_FOR_DATA + '.npy'
            trace_output_location = output_path + POSTFIX_FOR_TRACES + '.npy'
        case FileType.NPZ:
            trace_output_location = output_path + '.npz'
        case FileType.TRS:
            trace_output_location = output_path + '.trs'
        case _:
            raise Exception('Unsupported output file type')
    return data_output_location, trace_output_location


def get_data_path(data_path: str, traces_path: str) -> str:
    if data_path == '':
        return remove_extension_with_postfix(traces_path, POSTFIX_FOR_TRACES) + '_data.npy'
    else:
        return data_path
