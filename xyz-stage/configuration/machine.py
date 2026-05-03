from configuration.schema import MachineSettings


MACHINE_STEPS_PER_MM = {"X": 1600.0, "Y": 1600.0, "Z": 800.0, "E": 325.0}
MACHINE_MAX_FEEDRATE = {"X": 2.5, "Y": 2.5, "Z": 2.5, "E": 1.0}
MACHINE_ACCELERATION = 2.0
MACHINE_HOP_HEIGHT = 1.0
MACHINE_AXIS_DIRECTIONS = {"X": True, "Y": False, "Z": False}
MACHINE_OCTOPRINT_URL = "http://localhost:5002"
MACHINE_API_KEY_ENV = "API_KEY_OCTO"
MACHINE_ENABLE_MOTION = True


def get_machine_settings() -> MachineSettings:
    return MachineSettings(
        steps_per_mm={k: float(v) for k, v in MACHINE_STEPS_PER_MM.items()},
        max_feedrate={k: float(v) for k, v in MACHINE_MAX_FEEDRATE.items()},
        acceleration=float(MACHINE_ACCELERATION),
        hop_height=float(MACHINE_HOP_HEIGHT),
        axis_directions={k: bool(v) for k, v in MACHINE_AXIS_DIRECTIONS.items()},
        octoprint_url=MACHINE_OCTOPRINT_URL,
        api_key_env=MACHINE_API_KEY_ENV,
        enable_motion=bool(MACHINE_ENABLE_MOTION),
    )
