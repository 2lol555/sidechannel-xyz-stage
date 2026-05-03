from Configuration.measurement.schema import TargetConfig


TARGET_KEY_LENGTH_BYTES: int = 16
TARGET_FIXED_NONCE: bytes = bytes(16)
TARGET_TVLA_FIXED_PLAINTEXT: bytes = bytes.fromhex("DA39A3EE5E6B4B0D3255BFEF95601890")
TARGET_CIPHERTEXT_TIMEOUT_MS: int = 250
TARGET_CAPTURE_START_DELAY_S: float = 0.05


def get_target_config() -> TargetConfig:
    return TargetConfig(
        key_length_bytes=TARGET_KEY_LENGTH_BYTES,
        fixed_nonce=TARGET_FIXED_NONCE,
        tvla_fixed_plaintext=TARGET_TVLA_FIXED_PLAINTEXT,
        ciphertext_timeout_ms=TARGET_CIPHERTEXT_TIMEOUT_MS,
        capture_start_delay_s=TARGET_CAPTURE_START_DELAY_S,
    )
