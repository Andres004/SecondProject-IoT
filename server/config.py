"""Configuration of the control server.

Every tunable value of the server lives here, so the code has no magic
numbers. These values must match the ones documented in the report.
"""

from pathlib import Path

# Network
HOST = "0.0.0.0"  # Listen on every network interface of the PC.
PORT = 5050  # Must match SERVER_PORT in include/Secrets.h.
ACCEPT_TIMEOUT_S = 0.5  # Lets Ctrl+C stop the server on Windows.
SENSOR_TIMEOUT_S = 1.0  # Sensor silence after which it is considered lost.
MAX_LINE_LENGTH = 32  # Longest valid protocol message, in characters.
IP_PROBE_ADDRESS = ("8.8.8.8", 80)  # Only used to find the LAN IP.

# Distance ranges (cm):
#   NEAR   = [MIN_VALID_CM, NEAR_MEDIUM_BOUNDARY_CM)
#   MEDIUM = [NEAR_MEDIUM_BOUNDARY_CM, MEDIUM_FAR_BOUNDARY_CM)
#   FAR    = [MEDIUM_FAR_BOUNDARY_CM, MAX_VALID_CM]
MIN_VALID_CM = 2.0  # The HC-SR04 blind zone ends here.
MAX_VALID_CM = 400.0  # HC-SR04 maximum range.
NEAR_MEDIUM_BOUNDARY_CM = 20.0
MEDIUM_FAR_BOUNDARY_CM = 40.0
HYSTERESIS_CM = 2.0
MAX_INVALID_READINGS = 3  # Consecutive invalid readings that enter ERROR.

# Event log
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_COLUMNS = ("t_ms", "event", "seq", "value", "zone", "latency_ms")

# Sensor simulator (test tool)
SIMULATOR_HOST = "127.0.0.1"
SIMULATOR_PERIOD_S = 0.5  # Slow enough to see every LED change on video.
