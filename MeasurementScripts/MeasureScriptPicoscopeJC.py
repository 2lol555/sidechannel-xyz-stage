"""Measurement script: PicoScope + ChipWhisperer Nano (SimpleSerial) AES.

This file was originally derived from a larger Leia/JavaCard measurement project.
It has been condensed to only what we need here:

- Connect to a PicoScope 3000A (ps3000a)
- Trigger on Channel A, rising edge at ~2V (threshold computed from ADC range)
- Capture power traces from Channel B
- Execute AES on a CWNano running SimpleSerial AES firmware
- Save traces using the existing GenericTraceCreator output pipeline
"""

import ctypes
import threading
import time
import copy
import os
from dataclasses import dataclass

import numpy as np

from picosdk.ps3000a import ps3000a as ps
from picosdk.functions import adc2mV, assert_pico_ok

from secrets import token_bytes

from trsfile import Trace, SampleCoding
from trsfile.parametermap import TraceParameterMap
from trsfile.traceparameter import ByteArrayParameter

from Common.Generics.GenericTraceCreator import GenericTraceCreator
from Common.Models.FileType import FileType
from Configuration.Constants import KEY_NAME, PLAIN_TEXT_NAME, NONCE_NAME
from Configuration.MeasurementScriptConstants import PICO_MAGIC_VALUE
from Configuration.measurement import MEASUREMENT_CONFIG
from Configuration.measurement.schema import MeasurementConfig

try:
    import chipwhisperer as cw
except Exception:  # pragma: no cover
    cw = None


@dataclass(frozen=True)
class PicoTriggerConfig:
    """ps3000a simple trigger config."""

    enabled: int = 1
    source: int = 0  # PS3000A_CHANNEL['PS3000A_CHANNEL_A'] is 0
    threshold_adc: int = 10000
    direction: int = 2  # PS3000A_THRESHOLD_DIRECTION['PS3000A_RISING'] is 2
    delay: int = 0
    auto_trigger_ms: int = 0


class CWNanoAes:
    """Minimal SimpleSerial AES driver for CWNano.

    Assumes a SimpleSerial AES firmware that supports:
      - 'k' command: set key (16 bytes)
      - 'p' command: encrypt plaintext (16 bytes) -> returns ciphertext
    """

    def __init__(self):
        if cw is None:
            raise ImportError(
                "chipwhisperer python package not available. Install it or ensure it is on PYTHONPATH."
            )
        self._scope = None
        self._target = None

    def connect(self) -> None:
        self._scope = cw.scope()
        self._target = cw.target(self._scope)

        self._scope.default_setup()
        self._scope.io.target_pwr = True

        self._scope.clock.clkgen_freq = 7370000

        self._scope.io.nrst = 'low'
        time.sleep(0.05)
        self._scope.io.nrst = 'high'
        time.sleep(0.2)

        self._target.baud = 38400

        self._target.flush()
        self._ktp = cw.ktp.Basic()

    def disconnect(self) -> None:
        try:
            if self._target is not None:
                self._target.dis()
        finally:
            if self._scope is not None:
                self._scope.dis()

    def set_key(self, key: bytes) -> None:
        assert len(key) == 16
        self._target.simpleserial_write('k', key)
        # give firmware time
        time.sleep(0.01)

    def next_key_pt(self) -> tuple[bytes, bytes]:
        """Generate next (key, plaintext) pair similarly to cw.ktp.Basic()."""
        key, pt = self._ktp.next()
        return bytes(key), bytes(pt)

    def encrypt(self, plaintext: bytes, timeout_ms: int = 250) -> bytes:
        assert len(plaintext) == 16
        # flush any stale output
        try:
            self._target.flush()
        except Exception:
            pass
        self._target.flush()
        self._target.simpleserial_write('p', plaintext)
        ct = self._target.simpleserial_read('r', 16, timeout=timeout_ms)
        if ct is None or len(ct) != 16:
            raise RuntimeError(f"Failed to read ciphertext from CWNano (got {ct}).")
        return ct


class MeasureScriptPicoscopeJC(GenericTraceCreator):
    """Main measurement script (kept name for compatibility with config/imports)."""

    def __init__(self, measurement_config: MeasurementConfig):
        pico_cfg = measurement_config.pico
        target_cfg = measurement_config.target
        runtime_cfg = measurement_config.runtime

        self.offset_mv: float = pico_cfg.offset_mv
        self.timebase: int = pico_cfg.timebase
        self.channel_a_range: int = pico_cfg.channel_a_range
        self.channel_b_range: int = pico_cfg.channel_b_range
        self.pre_trigger_samples: int = pico_cfg.pre_trigger_samples
        self.trigger_channel: int = pico_cfg.trigger_channel
        self.threshold: int = pico_cfg.trigger_threshold_adc
        self.trigger_direction: int = pico_cfg.trigger_direction
        self.trigger_delay: int = pico_cfg.trigger_delay
        self.auto_trigger_ms: int = pico_cfg.auto_trigger_ms
        self.ready_timeout_ms: int = runtime_cfg.ready_timeout_ms
        self.enable_picoscope: bool = runtime_cfg.enable_picoscope
        self.enable_chipwhisperer: bool = runtime_cfg.enable_chipwhisperer
        self._fixed_range_scale_mv: float = 1.0
        self.key_length_bytes: int = target_cfg.key_length_bytes
        self.ciphertext_timeout_ms: int = target_cfg.ciphertext_timeout_ms
        self.capture_start_delay_s: float = target_cfg.capture_start_delay_s
        self._nonce_zero: bytes = target_cfg.fixed_nonce
        if len(self._nonce_zero) != 16:
            raise ValueError("target.fixed_nonce must be exactly 16 bytes.")
        if self.key_length_bytes != 16:
            raise ValueError("Only 16-byte AES keys are supported.")

        self.pico_handle = self._setup_picoscope() if self.enable_picoscope else None
        if self.enable_picoscope:
            self._fixed_range_scale_mv = self._compute_fixed_range_scale_mv()

        self.cw = None
        if self.enable_chipwhisperer:
            self.cw = CWNanoAes()
            self.cw.connect()

        super().__init__(measurement_config.output.to_trace_creator_config())
        if self.output_trace_count < 1:
            raise ValueError("Trace count must be >= 1.")

        # AES key used for all traces (matches prior scripts); can be changed to per-trace if desired.
        self.key: bytes = token_bytes(self.key_length_bytes)
        print(f"Using AES Key: 0x{self.key.hex().upper()}")
        print(f"Trace normalization: fixed_range_peak (mV at int8 full-scale={self._fixed_range_scale_mv:.3f})")
        if self.enable_chipwhisperer:
            self.cw.set_key(self.key)

        print(f'Trace output will be saved to: "{self.output_path}"')
        if self.data_output_path:
            print(f'Trace parameter data will be saved to: "{self.data_output_path}"')

    def _compute_fixed_range_scale_mv(self) -> float:
        max_adc = ctypes.c_int16(PICO_MAGIC_VALUE)
        probe_adc = (ctypes.c_int16 * 1)(PICO_MAGIC_VALUE)
        probe_mv = adc2mV(probe_adc, self.channel_b_range, max_adc)
        probe_arr = np.asarray(probe_mv, dtype=np.float64)
        scale = float(np.max(np.abs(probe_arr)))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError(
                f"Failed to derive fixed-range scale for channel range {self.channel_b_range}: {scale}"
            )
        return scale

    def _scale_trace_to_int8(self, adc_mv_trace: np.ndarray) -> np.ndarray:
        adc_mv_trace = np.asarray(adc_mv_trace, dtype=np.float64)
        scaled = adc_mv_trace / (self._fixed_range_scale_mv / 127.0)
        return np.clip(scaled, -128, 127).astype(np.int8)

    def prepare_output(self, filename: str | None = None) -> None:
        """Reinitialize output buffers/file handles for a new run on the same device session."""
        if filename:
            self.output_name = filename

        # Only reset trace output state; keep connected hardware/session intact.
        GenericTraceCreator.cleanup(self)
        self.data_output_path, self.output_path = self._get_output_paths()
        self.output_data, self.output_traces, self.output_traceset = self._create_output()
        print(f'Prepared trace output file: "{self.output_path}"')

    def cleanup(self):
        if self.cw is not None:
            try:
                self.cw.disconnect()
            except Exception:
                pass
        if self.pico_handle is not None:
            ps.ps3000aStop(self.pico_handle)
            ps.ps3000aCloseUnit(self.pico_handle)
        super().cleanup()

    def _setup_picoscope(self):
        scope_handle = ctypes.c_int16()
        status = {'openunit': ps.ps3000aOpenUnit(ctypes.byref(scope_handle), None)}
        assert_pico_ok(status['openunit'])

        # Channel A: trigger input (2V rising).
        status['setChA'] = ps.ps3000aSetChannel(
            scope_handle,
            0,  # A
            1,  # enabled
            1,  # DC coupling (PS3000A_DC = 1)
            self.channel_a_range,
            0.0,
        )
        assert_pico_ok(status['setChA'])

        # Channel B: power measurement.
        status['setChB'] = ps.ps3000aSetChannel(
            scope_handle,
            1,  # B
            1,
            1,
            self.channel_b_range,
            self.offset_mv,
        )
        assert_pico_ok(status['setChB'])

        # Trigger: Channel A rising
        # threshold is in ADC counts for ps3000aSetSimpleTrigger.
        # Config uses: int(3 / 10 * PICO_MAGIC_VALUE) (historical).
        # You requested ~2V. We keep using config-provided threshold, but log what it corresponds to.
        trig = PicoTriggerConfig(
            enabled=1,
            source=self.trigger_channel,
            threshold_adc=self.threshold,
            direction=self.trigger_direction,
            delay=self.trigger_delay,
            auto_trigger_ms=self.auto_trigger_ms,
        )
        status['trigger'] = ps.ps3000aSetSimpleTrigger(
            scope_handle,
            trig.enabled,
            trig.source,
            trig.threshold_adc,
            trig.direction,
            trig.delay,
            trig.auto_trigger_ms,
        )
        assert_pico_ok(status['trigger'])

        print(
            f"PicoScope trigger: ch={trig.source}, direction={trig.direction}, threshold_adc={self.threshold}, "
            f"pre_trigger_samples={self.pre_trigger_samples}, auto_trigger_ms={trig.auto_trigger_ms}"
        )
        return scope_handle

    def _capture_trace(self, key: bytes, plaintext: bytes, index: int, save_trace: bool = True):
        max_samples: int = self.pre_trigger_samples + self.output_sample_to

        if not self.enable_picoscope:
            return

        buffer_b_max = (ctypes.c_int16 * max_samples)()
        buffer_b_min = (ctypes.c_int16 * max_samples)()

        # ps3000a buffers
        # Channel B: power trace
        status = ps.ps3000aSetDataBuffers(
            self.pico_handle,
            1,  # B
            ctypes.byref(buffer_b_max),
            ctypes.byref(buffer_b_min),
            max_samples,
            0,
            0,
        )
        assert_pico_ok(status)

        time_intervals = ctypes.c_float()
        returned_max_samples = ctypes.c_int32()
        status = ps.ps3000aGetTimebase2(
            self.pico_handle,
            self.timebase,
            max_samples,
            ctypes.byref(time_intervals),
            1,  # oversample
            ctypes.byref(returned_max_samples),
            0,  # segment index
        )
        assert_pico_ok(status)

        # 0% pre-trigger => pass preTriggerSamples=0 when config requests it.
        pre = int(self.pre_trigger_samples)
        post = int(self.output_sample_to)
        time_indisposed = ctypes.c_int32()
        status = ps.ps3000aRunBlock(
            self.pico_handle,
            pre,
            post,
            self.timebase,
            1,
            None,
            0,
            None,
            None,
        )
        assert_pico_ok(status)

        ready = ctypes.c_int16(0)
        wait_started = time.monotonic()
        while ready.value == 0:
            ps.ps3000aIsReady(self.pico_handle, ctypes.byref(ready))
            waited_ms = int((time.monotonic() - wait_started) * 1000)
            if waited_ms > self.ready_timeout_ms:
                raise TimeoutError(
                    f"Capture did not become ready within {self.ready_timeout_ms}ms "
                    f"(trigger_channel={self.trigger_channel}, threshold_adc={self.threshold})."
                )

        overflow = ctypes.c_int16()
        c_max_samples = ctypes.c_int32(max_samples)
        status = ps.ps3000aGetValues(
            self.pico_handle,
            0,
            ctypes.byref(c_max_samples),
            1,
            0,
            0,
            ctypes.byref(overflow),
        )
        assert_pico_ok(status)

        max_adc = ctypes.c_int16(PICO_MAGIC_VALUE)
        adc_mv_ch_b_max = adc2mV(buffer_b_max, self.channel_b_range, max_adc)
        captured_trace = self._scale_trace_to_int8(adc_mv_ch_b_max)[self.output_sample_from:self.output_sample_to]

        if not save_trace:
            return

        if self.is_output_numpy:
            self.output_parameters.write_parameter_to_array(
                self.output_data[index], KEY_NAME, np.frombuffer(key, dtype=np.uint8)
            )
            self.output_parameters.write_parameter_to_array(
                self.output_data[index], PLAIN_TEXT_NAME, np.frombuffer(plaintext, dtype=np.uint8)
            )
            self.output_parameters.write_parameter_to_array(
                self.output_data[index], NONCE_NAME, np.frombuffer(self._nonce_zero, dtype=np.uint8)
            )
            self.output_traces[index] = captured_trace
        elif self.output_type == FileType.TRS:
            trace_parameters = TraceParameterMap(
                {
                    'KEY': ByteArrayParameter(key),
                    'PT': ByteArrayParameter(plaintext),
                    'NONCE': ByteArrayParameter(self._nonce_zero),
                }
            )
            self.output_traceset.append(Trace(SampleCoding.BYTE, captured_trace, trace_parameters))
        else:
            raise Exception(f'Unsupported output type: {self.output_type.name}')

    def _encrypt_and_capture(self, plaintext: bytes, index: int, save: bool = True):
        # Pass key explicitly to avoid race when key changes each trace.
        key_for_trace = self.key
        capture_thread = threading.Thread(target=self._capture_trace, args=(key_for_trace, plaintext, index, save))
        capture_thread.start()
        time.sleep(self.capture_start_delay_s)

        if self.enable_chipwhisperer:
            self.cw.encrypt(plaintext, timeout_ms=self.ciphertext_timeout_ms)

        capture_thread.join()

    def run(self):
        start_time = time.time()
        save_traces = self.enable_picoscope

        dummy_plaintext = bytes(16)
        self._encrypt_and_capture(dummy_plaintext, -1, save=False)

        for index in range(self.output_trace_count):
            plaintext = token_bytes(self.key_length_bytes)
            if index % 10 == 0 or index == self.output_trace_count - 1:
                print(f'Capturing trace {index + 1}/{self.output_trace_count}...')
            self._encrypt_and_capture(plaintext, index, save=save_traces)

        if save_traces:
            self.save_output()
        else:
            # No PicoScope capture: remove any pre-created output artifacts.
            GenericTraceCreator.cleanup(self)
            if self.output_path and os.path.exists(self.output_path):
                os.remove(self.output_path)
            if self.data_output_path and os.path.exists(self.data_output_path):
                os.remove(self.data_output_path)
        elapsed = time.time() - start_time
        print(f'Total execution time: {elapsed:.2f} seconds')

def setupTraceCapture(filename = None, output_folder = None) ->  MeasureScriptPicoscopeJC:
    measurement_config = copy.deepcopy(MEASUREMENT_CONFIG)

    if output_folder:
        measurement_config.output.output_folder_path = output_folder
    if filename:
        measurement_config.output.output_file_name = filename

    measure_script = MeasureScriptPicoscopeJC(measurement_config)

    return measure_script


def runTraceCapture(measure_script: MeasureScriptPicoscopeJC, filename ):
    measure_script.prepare_output(filename)
    measure_script.run()

def cleanupTraceCapture(measure_script: MeasureScriptPicoscopeJC ):
    measure_script.cleanup()


if __name__ == '__main__':
    measure_script_2 = MeasureScriptPicoscopeJC(MEASUREMENT_CONFIG)
    measure_script_2.run()
