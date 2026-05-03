from configuration.schema import ScanSettings


SCAN_CHIP_SIZE = (5.0, 7.0)
SCAN_STEP_SIZE = (1.0, 1.0)
SCAN_OUTPUT_ROOT = "/home/xpolakov/data/"


def get_scan_settings() -> ScanSettings:
    return ScanSettings(
        chip_size=(float(SCAN_CHIP_SIZE[0]), float(SCAN_CHIP_SIZE[1])),
        step_size=(float(SCAN_STEP_SIZE[0]), float(SCAN_STEP_SIZE[1])),
        output_root=SCAN_OUTPUT_ROOT,
    )

