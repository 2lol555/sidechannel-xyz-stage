from Configuration.measurement.schema import RuntimeConfig


RUNTIME_READY_TIMEOUT_MS: int = 5000
RUNTIME_ENABLE_PICOSCOPE: bool = True
RUNTIME_ENABLE_CHIPWHISPERER: bool = True


def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        ready_timeout_ms=RUNTIME_READY_TIMEOUT_MS,
        enable_picoscope=RUNTIME_ENABLE_PICOSCOPE,
        enable_chipwhisperer=RUNTIME_ENABLE_CHIPWHISPERER,
    )
