"""OctoPrint API wrapper."""

import os
import time
from typing import Dict, Optional

from config import DEFAULT_MAX_FEEDRATE, DEFAULT_STEPS_PER_MM, DEFAULT_ACCELERATION

import requests
from tqdm import tqdm

from logger import success, warning


class OctoPrintCommunicator:
    """OctoPrint transport + motion helpers."""

    DEFAULT_URL = "http://localhost:5002"
    DEFAULT_API_KEY_ENV = 'API_KEY_OCTO'
    DEFAULT_HOP_HEIGHT = 5.0

    def __init__(self, url: Optional[str] = None, api_key_env: Optional[str] = None) -> None:
        """Create communicator. Reads API key from env var."""
        self.url = url or self.DEFAULT_URL
        self.api_key_env = api_key_env or self.DEFAULT_API_KEY_ENV
        self.headers = { "X-Api-Key": os.environ.get(self.api_key_env) }
        self.max_feedrate = DEFAULT_MAX_FEEDRATE.copy()
        self.steps_per_mm = DEFAULT_STEPS_PER_MM.copy()
        self.acceleration = DEFAULT_ACCELERATION
        self.hop_height = self.DEFAULT_HOP_HEIGHT
        self.axis_dir = { 'X': 1.0, 'Y': 1.0, 'Z': 1.0 }
        self.enable_motion = True

    def set_config(self, octoprint_url: Optional[str] = None, api_key_env_var: Optional[str] = None) -> None:
        """Update URL and API key env var."""
        if octoprint_url:
            self.url = octoprint_url
        if api_key_env_var:
            self.api_key_env = api_key_env_var
        self.headers = { "X-Api-Key": os.environ.get(self.api_key_env) }

    def set_printer_settings(self, feedrate: Optional[Dict[str, float]] = None,
                             steps: Optional[Dict[str, float]] = None,
                             accel: Optional[float] = None,
                             hop_height: Optional[float] = None) -> None:
        """Update movement params used for timing and hopping."""
        if feedrate:
            self.max_feedrate.update(feedrate)
        if steps:
            self.steps_per_mm.update(steps)
        if accel is not None:
            self.acceleration = accel
        if hop_height is not None:
            self.hop_height = max(0.0, float(hop_height))

    def apply_printer_settings(self) -> None:
        """Send movement parameters to firmware using current communicator settings."""
        if not self.enable_motion:
            return
        steps_cmd = (
            f"M92 X{self.steps_per_mm['X']} Y{self.steps_per_mm['Y']} "
            f"Z{self.steps_per_mm['Z']} E{self.steps_per_mm['E']}"
        )
        feedrate_cmd = (
            f"M203 X{self.max_feedrate['X']} Y{self.max_feedrate['Y']} "
            f"Z{self.max_feedrate['Z']} E{self.max_feedrate['E']}"
        )
        accel_cmd = f"M204 P{self.acceleration} T{self.acceleration}"
        max_accel_cmd = (
            f"M201 X{self.acceleration} Y{self.acceleration} "
            f"Z{self.acceleration} E{self.acceleration}"
        )

        self.send_gcode_command(steps_cmd)
        self.send_gcode_command(feedrate_cmd)
        self.send_gcode_command(max_accel_cmd)
        self.send_gcode_command(accel_cmd)
        self.send_gcode_command("M18 S0")
        self.send_gcode_command("M17")

    def set_axis_directions(self, dirs: Optional[Dict[str, bool]] = None) -> None:
        """Update axis flip mapping (True = flipped direction)."""
        if dirs:
            for axis, flipped in dirs.items():
                if axis in self.axis_dir:
                    self.axis_dir[axis] = -1.0 if flipped else 1.0

    def wait_for_move_completion(self, x: float, y: float, z: float, hop: bool = True) -> None:
        """Sleep for estimated move duration."""
        total_time_sec = 0.0
        z_rate = self.max_feedrate.get('Z', DEFAULT_MAX_FEEDRATE['Z'])
        x_rate = self.max_feedrate.get('X', DEFAULT_MAX_FEEDRATE['X'])
        y_rate = self.max_feedrate.get('Y', DEFAULT_MAX_FEEDRATE['Y'])

        total_z_distance = abs(z)

        if hop and (x != 0 or y != 0):
            total_z_distance += 2.0 * self.hop_height

        total_time_sec += total_z_distance / z_rate
        if x != 0 or y != 0:
            time_xy_sec = max(
                abs(x) / x_rate if x != 0 else 0,
                abs(y) / y_rate if y != 0 else 0
            )
            total_time_sec += time_xy_sec

        total_time_sec += 0.5
        total_time_sec *= 1.5
        if total_time_sec > 0:
            steps = int(total_time_sec / 0.1) + 1
            with tqdm(total=steps, desc="Moving head", unit="0.1s", leave=False) as pbar:
                for _ in range(steps):
                    time.sleep(min(0.1, total_time_sec))
                    pbar.update(1)
                    total_time_sec -= 0.1
                    if total_time_sec <= 0:
                        break

    def move_head_by(self, x: float, y: float, z: float, hop: bool = True) -> None:
        """Move head by deltas."""
        dx = x * self.axis_dir.get('X', 1.0)
        dy = y * self.axis_dir.get('Y', 1.0)
        dz = z * self.axis_dir.get('Z', 1.0)
        if not self.enable_motion:
            return
        path = "/api/printer/printhead"

        if hop and (dx != 0 or dy != 0):
            if dz > 0:
                z_up = self.hop_height + dz
                z_down = -self.hop_height
            else:
                z_up = self.hop_height
                z_down = dz - self.hop_height
            requests.post(self.url + path,
                          json={ "command": "jog", "x": 0, "y": 0, "z": z_up },
                          headers=self.headers)
            requests.post(self.url + path,
                          json={ "command": "jog", "x": dx, "y": dy, "z": 0 },
                          headers=self.headers)
            requests.post(self.url + path,
                          json={ "command": "jog", "x": 0, "y": 0, "z": z_down },
                          headers=self.headers)
        else:
            if dz > 0:
                requests.post(self.url + path, json={ "command": "jog", "x": 0, "y": 0, "z": dz }, headers=self.headers)
                requests.post(self.url + path, json={ "command": "jog", "x": dx, "y": dy, "z": 0 },
                              headers=self.headers)
            else:
                requests.post(self.url + path, json={ "command": "jog", "x": dx, "y": dy, "z": 0 },
                              headers=self.headers)
                requests.post(self.url + path, json={ "command": "jog", "x": 0, "y": 0, "z": dz }, headers=self.headers)

        self.wait_for_move_completion(dx, dy, dz, hop)

    def query_printer_ready(self) -> bool:
        """Return whether printer is operational."""
        path = "/api/printer"
        response = requests.get(self.url + path, headers=self.headers)
        data = response.json()
        if data["state"]["flags"]["operational"]:
            success("Move complete or printer ready")
            return True
        warning("Still moving or not ready")
        return False

    def send_gcode_command(self, command: str) -> None:
        """POST a G-code command."""
        if not self.enable_motion:
            return
        path = "/api/printer/command"
        data = { "commands": [command] }
        response = requests.post(self.url + path, json=data, headers=self.headers)
        if response.status_code != 204:
            raise Exception(f"Printer rejected gcode: {command}")

    def set_motion_enabled(self, enabled: bool) -> None:
        self.enable_motion = bool(enabled)


communicator = OctoPrintCommunicator()


def set_octoprint_config(octoprint_url: Optional[str] = None, api_key_env_var: Optional[str] = None) -> None:
    communicator.set_config(octoprint_url, api_key_env_var)


def set_printer_settings(feedrate: Optional[Dict[str, float]], steps: Optional[Dict[str, float]],
                         accel: Optional[float] = None,
                         hop_height: Optional[float] = None) -> None:
    communicator.set_printer_settings(feedrate, steps, accel, hop_height)


def apply_printer_settings(feedrate: Optional[Dict[str, float]], steps: Optional[Dict[str, float]],
                           accel: Optional[float] = None,
                           hop_height: Optional[float] = None) -> None:
    """Apply settings to communicator and firmware in one call."""
    communicator.set_printer_settings(feedrate, steps, accel, hop_height)
    communicator.apply_printer_settings()


def set_axis_directions(dirs: Optional[Dict[str, bool]] = None) -> None:
    communicator.set_axis_directions(dirs)


def set_motion_enabled(enabled: bool) -> None:
    communicator.set_motion_enabled(enabled)


def wait_for_move_completion(x: float, y: float, z: float, hop: bool = True) -> None:
    communicator.wait_for_move_completion(x, y, z, hop)


def move_head_by(x: float, y: float, z: float, hop: bool = True) -> None:
    communicator.move_head_by(x, y, z, hop)


def query_printer_ready() -> bool:
    return communicator.query_printer_ready()


def send_gcode_command(command: str) -> None:
    communicator.send_gcode_command(command)
