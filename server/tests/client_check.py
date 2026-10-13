"""Automatic test of the ESP32 firmware, with a fake server.

The script takes the place of tcp_server.py: it listens on the same port,
waits for one ESP32, sends it messages and checks every answer. It needs
tcp_server.py stopped and only one board powered:

    python -m tests.client_check ActuatorCheck    (OI-2 on, OI-1 off)
    python -m tests.client_check SensorCheck      (OI-1 on, OI-2 off)

The steps of each class run in order, on the same connection.
"""

import re
import socket
import time
import unittest

import config
from tests.system_check import Connection

WAIT_FOR_BOARD_S = 30.0  # Longest wait for the ESP32 to connect.
REPLY_TIMEOUT_S = 1.0  # Longest wait for an answer that travels by WiFi.
SILENCE_S = 0.5  # Wait used to check that no answer arrives.
SHOW_S = 1.5  # Time each valid command stays on the LEDs, for the video.
OUTAGE_S = 6.0  # Time the fake server stays closed.
MAX_RECONNECT_S = 3.0  # RNF5: from listening again to the REGISTER.
SAMPLE_S = 5.0  # Window used to measure the readings of OI-1.
CONTINUE_S = 2.0  # Readings checked after sending lines to OI-1.
MIN_READINGS_PER_S = 5  # RNF4.
POST_FORMAT = re.compile(r"POST (\d+) (\d+\.\d|NAN)")  # One decimal or NAN.

# Every LED in every mode. OI-2 must apply each one and answer ACK.
VALID_COMMANDS = [
    "SET 1 RED ON", "SET 2 RED BLINK", "SET 3 YELLOW ON",
    "SET 4 YELLOW BLINK", "SET 5 WHITE ON", "SET 6 WHITE BLINK",
    "SET 7 ALL ON", "SET 8 ALL BLINK"]
# Lines of exactly 32 and 33 characters: the longest valid one and the
# shortest one that the ESP32 must discard.
LONGEST_SET = "SET " + "0" * 19 + "15 RED ON"
TOO_LONG_SET = "SET " + "0" * 20 + "16 RED ON"
# Lines that OI-2 must ignore: no ACK and no change on the LEDs.
INVALID_LINES = [
    "SET 9 BLUE ON",  # Unknown LED.
    "SET 10 RED",  # Missing mode.
    "SET x RED ON",  # seq is not a number.
    "SET 11 red on",  # Names must be in capitals.
    "SET 12 RED BLINKING",  # Unknown mode.
    "",  # Empty line.
    "OK",
    "ERROR BAD_FORMAT",
    "HELLO",
    TOO_LONG_SET,
]
# Lines that OI-1 must ignore while it keeps sending readings.
SENSOR_LINES = ["OK", "ERROR BAD_FORMAT", "SET 1 RED ON", "X" * 40]


def wait_for_board(timeout: float) -> Connection:
    """Listen on the server port until the ESP32 connects, then stop."""
    # The listening socket is closed as soon as the board connects, so no
    # other client can connect while the test runs.
    with socket.create_server((config.HOST, config.PORT)) as listener:
        listener.settimeout(timeout)
        try:
            sock, _ = listener.accept()
        except TimeoutError:
            message = f"no ESP32 connected within {timeout:.0f} s"
            raise TimeoutError(message) from None
    # Like the real server, short messages leave at once.
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return Connection(sock)


class BoardCase(unittest.TestCase):
    """Fake server shared by the steps of one board."""

    role = ""  # REGISTER role of the board under test.
    board: Connection

    @classmethod
    def setUpClass(cls) -> None:
        """Wait for the board before the first step."""
        print(f"\nWaiting for the {cls.role} board on port {config.PORT}...")
        cls.board = wait_for_board(WAIT_FOR_BOARD_S)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the connection after the last step."""
        cls.board.close()

    def reconnect(self) -> None:
        """Close the server for OUTAGE_S and wait for the board to return."""
        # While nobody listens, the board must show it lost the server and
        # try again every 2 s.
        self.board.close()
        print(f"\n  server closed for {OUTAGE_S:.0f} s", end="")
        time.sleep(OUTAGE_S)
        # From now on the board has MAX_RECONNECT_S to register again.
        started = time.monotonic()
        try:
            type(self).board = wait_for_board(MAX_RECONNECT_S)
        except TimeoutError:
            self.fail(f"the board did not return within {MAX_RECONNECT_S} s")
        first_line = self.board.receive(REPLY_TIMEOUT_S)
        elapsed = time.monotonic() - started
        print(f"; {first_line} {elapsed * 1000:.0f} ms after listening "
              "again", end=" ")
        # The first message after reconnecting must be the registration.
        self.assertEqual(first_line, f"REGISTER {self.role}")
        self.assertLessEqual(elapsed, MAX_RECONNECT_S)
        self.board.send("OK")


class ActuatorCheck(BoardCase):
    """B05-A: firmware of OI-2. Run it with OI-2 on and OI-1 off."""

    role = "ACTUATOR"

    def expect_ack(self, command: str) -> None:
        """Send a valid SET and check that its ACK comes back."""
        started = time.monotonic()
        self.board.send(command)
        seq = int(command.split()[1])
        self.assertEqual(self.board.receive(REPLY_TIMEOUT_S), f"ACK {seq}",
                         command)
        elapsed = time.monotonic() - started
        print(f"\n  {command}: ACK after {elapsed * 1000:.0f} ms", end="")

    def test_1_registers_first(self):
        """RF4: the first message of OI-2 is REGISTER ACTUATOR."""
        self.assertEqual(self.board.receive(REPLY_TIMEOUT_S),
                         "REGISTER ACTUATOR")
        self.board.send("OK")

    def test_2_applies_every_command(self):
        """RF3, RF4: every LED in every mode is applied and confirmed."""
        for command in [*VALID_COMMANDS, LONGEST_SET]:
            self.expect_ack(command)
            time.sleep(SHOW_S)  # Time to see the LEDs in the video.
        print(end=" ")

    def test_3_ignores_invalid_lines(self):
        """A line that is not a valid SET gets no ACK and changes nothing."""
        self.expect_ack("SET 13 WHITE ON")
        # OI-2 only answers valid SET commands, so nothing must come back.
        for line in INVALID_LINES:
            self.board.send(line)
            self.assertIsNone(self.board.receive(SILENCE_S), line)
        # The connection still works after all the invalid lines.
        self.expect_ack("SET 14 RED BLINK")
        print(end=" ")

    def test_4_shows_error_and_reconnects(self):
        """RF7 (b), RF7 (c): without server OI-2 shows ERROR, then returns."""
        self.reconnect()
        self.expect_ack("SET 0 WHITE ON")
        print(end=" ")


class SensorCheck(BoardCase):
    """B05-B: firmware of OI-1. Run it with OI-1 on and OI-2 off."""

    role = "SENSOR"
    last_seq = 0  # seq of the last reading received so far.

    def read_posts(self, seconds: float) -> list[int]:
        """Read POST lines during that time, check them and return seqs."""
        seqs: list[int] = []
        deadline = time.monotonic() + seconds
        # Lines are read until the time is over; each one must be a POST.
        while (remaining := deadline - time.monotonic()) > 0:
            line = self.board.receive(remaining)
            if line is None:
                break
            match = POST_FORMAT.fullmatch(line)
            self.assertIsNotNone(match, f"not a valid POST: {line!r}")
            seqs.append(int(match[1]))
        self.assertTrue(seqs, "no readings arrived")
        return seqs

    def assert_consecutive(self, seqs: list[int]) -> None:
        """Check that seq grows by one from the last reading received."""
        expected = list(range(self.last_seq + 1, self.last_seq + 1
                              + len(seqs)))
        self.assertEqual(seqs, expected)
        type(self).last_seq = seqs[-1]

    def test_1_registers_first_without_waiting(self):
        """RF4: OI-1 registers first and sends readings before the OK."""
        self.assertEqual(self.board.receive(REPLY_TIMEOUT_S),
                         "REGISTER SENSOR")
        # The OK is held back: the readings must arrive anyway.
        seqs = self.read_posts(SILENCE_S)
        self.board.send("OK")
        type(self).last_seq = seqs[-1]

    def test_2_readings_format_and_rate(self):
        """RF1, RNF4: one decimal or NAN, seq + 1, at least 5 per second."""
        seqs = self.read_posts(SAMPLE_S)
        self.assert_consecutive(seqs)
        rate = len(seqs) / SAMPLE_S
        print(f"\n  {len(seqs)} readings in {SAMPLE_S:.0f} s = {rate:.1f} "
              "per second", end=" ")
        self.assertGreaterEqual(rate, MIN_READINGS_PER_S)

    def test_3_ignores_server_lines(self):
        """OK, ERROR, SET and too long lines do not stop the readings."""
        # OI-1 must keep sending without skipping any seq.
        for line in SENSOR_LINES:
            self.board.send(line)
        self.assert_consecutive(self.read_posts(CONTINUE_S))

    def test_4_reconnects_without_restart(self):
        """RF7 (c): OI-1 returns without restarting; seq kept growing."""
        self.reconnect()
        seqs = self.read_posts(SILENCE_S)
        jump = seqs[0] - self.last_seq
        print(f"\n  seq jumped from {self.last_seq} to {seqs[0]}", end=" ")
        # Readings taken while disconnected also used a seq.
        self.assertGreaterEqual(jump, OUTAGE_S * MIN_READINGS_PER_S)


if __name__ == "__main__":
    unittest.main(verbosity=2)
