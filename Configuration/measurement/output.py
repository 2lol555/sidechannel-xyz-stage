from Common.Models.FileType import FileType
from Common.Models.ParameterDefinition import ParameterDefinition
from Configuration.Constants import KEY_NAME, NONCE_NAME, PLAIN_TEXT_NAME
from Configuration.measurement.schema import OutputConfig
from Helpers.ParameterWrapper import ParameterWrapper


OUTPUT_TRACE_COUNT: int = 200
OUTPUT_SAMPLE_START: int = 0
OUTPUT_SAMPLE_END: int = 400_000
OUTPUT_FOLDER_PATH: str = "/home/xpolakov/data/"
OUTPUT_FILE_NAME: str = "xyz-capture"
OUTPUT_FILE_TYPE: FileType = FileType.TRS

OUTPUT_PARAMETERS: ParameterWrapper = ParameterWrapper(
    [
        ParameterDefinition(KEY_NAME, 16),
        ParameterDefinition(PLAIN_TEXT_NAME, 16),
        ParameterDefinition(NONCE_NAME, 16),
    ]
)


def get_output_config() -> OutputConfig:
    return OutputConfig(
        output_file_name=OUTPUT_FILE_NAME,
        output_folder_path=OUTPUT_FOLDER_PATH,
        output_type=OUTPUT_FILE_TYPE,
        output_parameters=OUTPUT_PARAMETERS,
        trace_count=OUTPUT_TRACE_COUNT,
        sample_start=OUTPUT_SAMPLE_START,
        sample_end=OUTPUT_SAMPLE_END,
    )
