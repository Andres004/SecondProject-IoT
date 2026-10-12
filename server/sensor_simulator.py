"""Fake sensor: sends exact distances to the server to test the boundaries.

Without arguments it sends BOUNDARY_SCENARIO; with arguments it sends those
values in the given order.
"""

import socket
import sys
import time

import config

# Readings that cross every boundary in both directions, then invalid ones.
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
    # Values given on the command line replace the built-in scenario.
    values = sys.argv[1:] or BOUNDARY_SCENARIO
    address = (config.SIMULATOR_HOST, config.PORT)
    with (socket.create_connection(address) as sock,
          sock.makefile("r", encoding="ascii") as reader):
        # Register first and show the answer of the server.
        sock.sendall(b"REGISTER SENSOR\n")
        print("REGISTER SENSOR ->", reader.readline().strip())
        # One POST per value, numbered from 1 like the real sensor.
        for seq, value in enumerate(values, start=1):
            message = f"POST {seq} {value}"
            sock.sendall((message + "\n").encode("ascii"))
            print(message)
            time.sleep(config.SIMULATOR_PERIOD_S)


if __name__ == "__main__":
    main()
