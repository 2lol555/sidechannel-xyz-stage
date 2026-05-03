from Configuration.MeasurementScriptConstants import PICO_MAGIC_VALUE
from Configuration.measurement.schema import PicoConfig

# TODO - pridat odkaz na picoscope manual a comments

PICO_OFFSET_MV: float = 0.0
PICO_TIMEBASE: int = 2
PICO_CHANNEL_A_RANGE: int = 8
PICO_CHANNEL_B_RANGE: int = 1
# 10% pre-trigger for current 250000-sample saved window.
PICO_PRE_TRIGGER_SAMPLES: int = 25_000
PICO_TRIGGER_CHANNEL: int = 0
PICO_TRIGGER_THRESHOLD_ADC: int = int(3 / 10 * PICO_MAGIC_VALUE)
PICO_TRIGGER_DIRECTION: int = 2
PICO_TRIGGER_DELAY: int = 0
PICO_AUTO_TRIGGER_MS: int = 10_000


def get_pico_config() -> PicoConfig:
    return PicoConfig(
        offset_mv=PICO_OFFSET_MV,
        timebase=PICO_TIMEBASE,
        channel_a_range=PICO_CHANNEL_A_RANGE,
        channel_b_range=PICO_CHANNEL_B_RANGE,
        pre_trigger_samples=PICO_PRE_TRIGGER_SAMPLES,
        trigger_channel=PICO_TRIGGER_CHANNEL,
        trigger_threshold_adc=PICO_TRIGGER_THRESHOLD_ADC,
        trigger_direction=PICO_TRIGGER_DIRECTION,
        trigger_delay=PICO_TRIGGER_DELAY,
        auto_trigger_ms=PICO_AUTO_TRIGGER_MS,
    )
