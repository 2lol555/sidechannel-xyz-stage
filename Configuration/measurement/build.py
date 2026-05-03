from Configuration.measurement.output import get_output_config
from Configuration.measurement.pico import get_pico_config
from Configuration.measurement.runtime import get_runtime_config
from Configuration.measurement.schema import MeasurementConfig
from Configuration.measurement.target import get_target_config


def get_measurement_config() -> MeasurementConfig:
    return MeasurementConfig(
        output=get_output_config(),
        pico=get_pico_config(),
        target=get_target_config(),
        runtime=get_runtime_config(),
    )


MEASUREMENT_CONFIG: MeasurementConfig = get_measurement_config()

