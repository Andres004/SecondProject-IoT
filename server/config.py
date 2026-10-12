"""Constants of the control server and of the sensor simulator."""

from pathlib import Path

# Network
HOST = "0.0.0.0"  # Accept connections on every network interface of the PC.
PORT = 5050  # TCP port where the server listens.
ACCEPT_TIMEOUT_S = 0.5  # accept() returns this often so Ctrl+C can stop it.
SENSOR_TIMEOUT_S = 1.0  # Silence after which the sensor is considered lost.
MAX_LINE_LENGTH = 32  # Longest valid message, in characters.
IP_PROBE_ADDRESS = ("8.8.8.8", 80)  # Public address used to find the LAN IP.

# Distance ranges (cm):
#   NEAR   = [MIN_VALID_CM, NEAR_MEDIUM_BOUNDARY_CM)
#   MEDIUM = [NEAR_MEDIUM_BOUNDARY_CM, MEDIUM_FAR_BOUNDARY_CM)
#   FAR    = [MEDIUM_FAR_BOUNDARY_CM, MAX_VALID_CM]
MIN_VALID_CM = 2.0  # Below this distance the HC-SR04 cannot measure.
MAX_VALID_CM = 400.0  # Longest distance the HC-SR04 can measure.
NEAR_MEDIUM_BOUNDARY_CM = 20.0  # First distance of MEDIUM.
MEDIUM_FAR_BOUNDARY_CM = 40.0  # First distance of FAR.
HYSTERESIS_CM = 2.0  # Distance past a boundary needed to change zone.
MAX_INVALID_READINGS = 3  # Invalid readings in a row that change to ERROR.

# Event log
LOG_DIR = Path(__file__).resolve().parent / "logs"  # Folder of the CSV files.
# Columns of the CSV file, in order.
LOG_COLUMNS = ("t_ms", "event", "seq", "value", "zone", "latency_ms")

# Sensor simulator
SIMULATOR_HOST = "127.0.0.1"  # The simulator runs on the server PC.
SIMULATOR_PERIOD_S = 0.5  # Time between two simulated readings.
