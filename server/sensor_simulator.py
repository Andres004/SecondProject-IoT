"""Fake sensor client: sends exact distances to test the range boundaries.

Run from the repository root while the server is running:
    python server/sensor_simulator.py              (built-in scenario)
    python server/sensor_simulator.py 25 19.9 NAN  (custom values, in order)
"""

import socket
import sys
import time

import config


#: Readings that cross every boundary up and down, plus invalid readings.
BOUNDARY_SCENARIO = [
    "10.0", "19.9", "20.0", "21.9", "22.0",  # NEAR -> MEDIUM at 22.0
    "39.9", "40.0", "41.9", "42.0",          # MEDIUM -> FAR at 42.0
    "38.0", "37.9",                          # FAR -> MEDIUM at 37.9
    "20.0", "18.0", "17.9",                  # MEDIUM -> NEAR at 17.9
    "NAN", "NAN", "NAN",                     # third invalid -> ERROR
    "1.9", "25.0",                           # blind zone, then recovery
]


def main() -> None:
    """Register as SENSOR and send one POST per value."""
    values = sys.argv[1:] or BOUNDARY_SCENARIO
    address = (config.SIMULATOR_HOST, config.PORT)
    with (socket.create_connection(address) as sock,
          sock.makefile("r", encoding="ascii") as reader):
        sock.sendall(b"REGISTER SENSOR\n")
        print("REGISTER SENSOR ->", reader.readline().strip())
        for seq, value in enumerate(values, start=1):
            message = f"POST {seq} {value}"
            sock.sendall((message + "\n").encode("ascii"))
            print(message)
            time.sleep(config.SIMULATOR_PERIOD_S)


if __name__ == "__main__":
    main()
