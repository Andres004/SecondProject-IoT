"""Automatic system tests of the running server, with fake OI-1 and OI-2.

The tests connect to the server as a sensor and as an actuator, send the
messages of each case and check every answer of the server. The fake
actuator confirms each command with ACK, like the real one. Some checks also
read the CSV log that the server is writing.

The server must be running on this PC and both ESP32 turned off, because a
client that registers takes the place of the real one. Each case ends with
the sensor disconnected, so the server is back in ERROR for the next case.

Usage, from the server folder:
    python -m tests.system_check
"""

import contextlib
import csv
import io
import socket
import struct
import tempfile
import time
import unittest
from pathlib import Path

import config
from sensor_simulator import BOUNDARY_SCENARIO
from tcp_server import ControlServer, EventLog

REPLY_TIMEOUT_S = 0.5  # Longest wait for an answer that must arrive.
SILENCE_S = 0.2  # Wait used to check that no answer arrives.
POLL_S = 0.05  # Time between two reads of the CSV log.
MAX_FAILSAFE_S = 1.5  # RF7 (a): ERROR reaches OI-2 within this time.
CLOCK_TOLERANCE_S = 0.05  # Timer resolution of the operating system.

# Messages of exactly 32 and 33 characters: the longest valid one and the
# shortest one that is too long.
LONGEST_POST = "POST 7 10." + "0" * 22
TOO_LONG_POST = "POST 6 10." + "0" * 23

# Invalid messages and the answer of the server to each one, in order.
UNREGISTERED_CASES = [
    ("POST 1 10.0", "ERROR NOT_REGISTERED"),
    ("HELLO", "ERROR NOT_REGISTERED"),
    ("REGISTER", "ERROR BAD_FORMAT"),
    ("REGISTER LAMP", "ERROR BAD_FORMAT"),
    ("REGISTER SENSOR X", "ERROR BAD_FORMAT"),
]
SENSOR_CASES = [
    ("", "ERROR BAD_FORMAT"),
    ("POST 2", "ERROR BAD_FORMAT"),
    ("POST 3 10.0 5", "ERROR BAD_FORMAT"),
    ("POST x 10.0", "ERROR BAD_FORMAT"),
    ("POST 4 abc", "ERROR BAD_FORMAT"),
    (TOO_LONG_POST, "ERROR BAD_FORMAT"),
    ("ACK 5", "ERROR UNKNOWN_CMD"),
    ("post 6 10.0", "ERROR UNKNOWN_CMD"),
]
ACTUATOR_CASES = [
    ("POST 8 10.0", "ERROR UNKNOWN_CMD"),
    ("ACK", "ERROR BAD_FORMAT"),
    ("ACK x", "ERROR BAD_FORMAT"),
]


class Connection:
    """One TCP connection that sends and receives lines of text."""

    def __init__(self, sock: socket.socket) -> None:
        """Wrap a socket that is already connected."""
        self.sock = sock
        self.buffer = b""

    def send(self, line: str) -> None:
        """Send one message followed by a newline."""
        self.sock.sendall((line + "\n").encode("ascii"))

    def receive(self, timeout: float = REPLY_TIMEOUT_S) -> str | None:
        """Return the next line, or None if none arrives within timeout."""
        deadline = time.monotonic() + timeout
        # Bytes are added to the buffer until it holds a whole line.
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self.sock.settimeout(remaining)
            try:
                data = self.sock.recv(1024)
            except TimeoutError:
                return None
            if not data:
                return None  # The other side closed the connection.
            self.buffer += data
        # The first line leaves the buffer; the rest waits for the next call.
        line, _, self.buffer = self.buffer.partition(b"\n")
        return line.decode("ascii", errors="replace").rstrip("\r")

    def close(self) -> None:
        """Close the connection."""
        self.sock.close()


def server_log() -> list[dict]:
    """Return the rows of the CSV that the running server is writing."""
    # The newest file belongs to the running server: names hold the time.
    newest = max(config.LOG_DIR.glob("server_*.csv"))
    with newest.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


class SystemCase(unittest.TestCase):
    """Helpers shared by the test classes."""

    def connect(self, role: str | None = None) -> Connection:
        """Open a connection and register it with role, if one is given."""
        client = Connection(socket.create_connection(
            (config.SIMULATOR_HOST, config.PORT), timeout=REPLY_TIMEOUT_S))
        # The connection is closed at the end of the case, even if it fails.
        self.addCleanup(client.close)
        if role is not None:
            client.send(f"REGISTER {role}")
            self.assertEqual(client.receive(), "OK")
        return client

    def expect_set(self, actuator: Connection, command: str) -> None:
        """Check the next SET and confirm it with ACK, as OI-2 does."""
        self.assertEqual(actuator.receive(), command)
        # The second word of "SET <seq> <led> <mode>" is the seq.
        actuator.send(f"ACK {command.split()[1]}")

    def register_actuator(self, state: str = "ALL BLINK") -> Connection:
        """Register a fake actuator, which first receives the state now."""
        actuator = self.connect("ACTUATOR")
        self.expect_set(actuator, f"SET 0 {state}")
        return actuator

    def close_sensor(self, sensor: Connection, actuator: Connection) -> None:
        """Close the sensor; the server must order ERROR to the actuator."""
        sensor.close()
        self.expect_set(actuator, "SET 0 ALL BLINK")

    def wait_for_row(self, first_row: int, event: str, **fields) -> dict:
        """Wait until the CSV has that event after first_row and return it."""
        # The server may write the row a moment after it answers, so the
        # CSV is read again until the row appears or the time runs out.
        deadline = time.monotonic() + REPLY_TIMEOUT_S
        while True:
            for row in server_log()[first_row:]:
                if row["event"] == event and all(
                        row[name] == value for name, value in fields.items()):
                    return row
            if time.monotonic() > deadline:
                self.fail(f"{event} {fields} is not in the server log")
            time.sleep(POLL_S)


class ProtocolTest(SystemCase):
    """B02: registration and answers to valid and invalid messages."""

    def test_register_and_initial_state(self):
        """REGISTER gets OK and the actuator receives the state at once."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        # The latency of the ACK is measured from the registration.
        row = self.wait_for_row(first_row, "ACK", seq="0")
        self.assertNotEqual(row["latency_ms"], "")
        sensor = self.connect("SENSOR")
        sensor.close()
        # The zone was already ERROR, so no command must arrive.
        self.assertIsNone(actuator.receive(SILENCE_S))

    def test_messages_without_waiting_for_ok(self):
        """A POST sent right after REGISTER, before the OK, is accepted."""
        actuator = self.register_actuator()
        sensor = self.connect()
        # Both messages travel together, before the OK can arrive.
        sensor.sock.sendall(b"REGISTER SENSOR\nPOST 1 10.0\n")
        self.assertEqual(sensor.receive(), "OK")
        self.expect_set(actuator, "SET 1 RED BLINK")
        self.close_sensor(sensor, actuator)

    def test_invalid_messages(self):
        """Each invalid message gets its ERROR and the connection stays."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        # First, messages from a connection that has not registered yet.
        sensor = self.connect()
        for message, answer in UNREGISTERED_CASES:
            sensor.send(message)
            self.assertEqual(sensor.receive(), answer, message)
        sensor.send("REGISTER SENSOR")
        self.assertEqual(sensor.receive(), "OK")
        for message, answer in SENSOR_CASES:
            sensor.send(message)
            self.assertEqual(sensor.receive(), answer, message)
        # After all the errors, the longest valid message still works.
        sensor.send(LONGEST_POST)
        self.expect_set(actuator, "SET 7 RED BLINK")
        self.assertIsNone(sensor.receive(SILENCE_S))
        # Messages that the actuator may not send.
        for message, answer in ACTUATOR_CASES:
            actuator.send(message)
            self.assertEqual(actuator.receive(), answer, message)
        self.close_sensor(sensor, actuator)
        # Each invalid message must also appear in the CSV.
        errors = [row for row in server_log()[first_row:]
                  if row["event"] == "PROTOCOL_ERROR"]
        self.assertEqual(len(errors), len(UNREGISTERED_CASES)
                         + len(SENSOR_CASES) + len(ACTUATOR_CASES))

    def test_ack_without_command(self):
        """An ACK with no command waiting gets no answer and no latency."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        actuator.send("ACK 99")
        self.assertIsNone(actuator.receive(SILENCE_S))
        row = self.wait_for_row(first_row, "ACK", seq="99")
        self.assertEqual(row["latency_ms"], "")


class ControlTest(SystemCase):
    """B03: commands produced by the readings, through TCP."""

    def run_scenario(self, readings: list[str], commands: list[str]) -> None:
        """Send the readings and check the exact list of commands."""
        actuator = self.register_actuator()
        sensor = self.connect("SENSOR")
        first_row = len(server_log())
        # All the readings go at once, numbered from 1 like OI-1 does.
        for seq, value in enumerate(readings, start=1):
            sensor.send(f"POST {seq} {value}")
        # The commands must arrive exactly in this order, and no others.
        for command in commands:
            self.expect_set(actuator, command)
        self.close_sensor(sensor, actuator)
        # Each ACK is logged with the latency of its command.
        self.wait_for_row(first_row, "ACK", seq="0")
        acks = {row["seq"]: row["latency_ms"] for row in server_log()[
            first_row:] if row["event"] == "ACK"}
        for command in commands:
            self.assertNotEqual(acks.get(command.split()[1], ""), "")

    def test_boundaries_and_hysteresis(self):
        """RF2, RF5: each boundary in both directions, with hysteresis."""
        self.run_scenario(BOUNDARY_SCENARIO, [
            "SET 1 RED BLINK", "SET 5 YELLOW BLINK", "SET 9 WHITE ON",
            "SET 11 YELLOW BLINK", "SET 14 RED BLINK", "SET 17 ALL BLINK",
            "SET 19 YELLOW BLINK"])

    def test_jumps_and_range_limits(self):
        """RF2, RF6: jumps NEAR <-> FAR and the limits 2.0 and 200.0 cm."""
        self.run_scenario([
            "10.0", "42.0", "17.9", "41.9", "2.0", "200.0", "200.1", "inf",
            "-5.0", "200.0"], [
            "SET 1 RED BLINK", "SET 2 WHITE ON", "SET 3 RED BLINK",
            "SET 4 YELLOW BLINK", "SET 5 RED BLINK", "SET 6 WHITE ON",
            "SET 9 ALL BLINK", "SET 10 WHITE ON"])

    def test_isolated_invalid_readings(self):
        """RF6: one or two invalid readings keep the zone; three give ERROR."""
        self.run_scenario([
            "30.0", "NAN", "NAN", "30.0", "NAN", "NAN", "18.0", "NAN", "NAN",
            "NAN", "25.0"], [
            "SET 1 YELLOW BLINK", "SET 10 ALL BLINK", "SET 11 YELLOW BLINK"])


class DisconnectionTest(SystemCase):
    """B04: clients that disconnect, go silent or are replaced."""

    def lose_sensor(self, close: bool, reason: str) -> float:
        """Lose the sensor, check ERROR in time and return how long it took."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        sensor = self.connect("SENSOR")
        sensor.send("POST 1 10.0")
        last_post = time.monotonic()
        self.expect_set(actuator, "SET 1 RED BLINK")
        # Either the sensor closes now, or it stays connected and silent.
        if close:
            sensor.close()
        self.assertEqual(actuator.receive(MAX_FAILSAFE_S), "SET 0 ALL BLINK")
        elapsed = time.monotonic() - last_post
        actuator.send("ACK 0")
        print(f"\n  ERROR reached the actuator {elapsed * 1000:.0f} ms after "
              "the last reading", end=" ")
        self.assertLessEqual(elapsed, MAX_FAILSAFE_S)
        self.wait_for_row(first_row, "DISCONNECT", value=f"SENSOR/{reason}")
        return elapsed

    def test_sensor_closes(self):
        """RF7 (a): the sensor closes its connection -> ERROR at once."""
        self.lose_sensor(close=True, reason="closed")

    def test_sensor_connection_error(self):
        """RF7 (a): the connection of the sensor breaks -> ERROR at once."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        sensor = self.connect("SENSOR")
        sensor.send("POST 1 10.0")
        self.expect_set(actuator, "SET 1 RED BLINK")
        # A linger time of 0 closes the socket with a reset, as a broken
        # connection does.
        sensor.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                               struct.pack("ii", 1, 0))
        sensor.close()
        self.expect_set(actuator, "SET 0 ALL BLINK")
        self.wait_for_row(first_row, "DISCONNECT", value="SENSOR/error")

    def test_silent_sensor(self):
        """RF7 (a): a sensor silent for 1.0 s is lost -> ERROR."""
        elapsed = self.lose_sensor(close=False, reason="timeout")
        self.assertGreaterEqual(
            elapsed, config.SENSOR_TIMEOUT_S - CLOCK_TOLERANCE_S)

    def test_sensor_replaced(self):
        """RF7 (c): a new sensor replaces the old one, which is ignored."""
        actuator = self.register_actuator()
        old_sensor = self.connect("SENSOR")
        old_sensor.send("POST 1 30.0")
        self.expect_set(actuator, "SET 1 YELLOW BLINK")
        new_sensor = self.connect("SENSOR")
        new_sensor.send("POST 1 10.0")
        self.expect_set(actuator, "SET 1 RED BLINK")
        # The replaced sensor is no longer registered: its readings are
        # rejected and do not change the zone.
        old_sensor.send("POST 2 50.0")
        self.assertEqual(old_sensor.receive(SILENCE_S), "ERROR NOT_REGISTERED")
        self.assertIsNone(actuator.receive(SILENCE_S))
        # Closing the replaced sensor must not put the system in ERROR.
        old_sensor.close()
        self.assertIsNone(actuator.receive(SILENCE_S))
        # The new sensor still controls the zone.
        new_sensor.send("POST 2 25.0")
        self.expect_set(actuator, "SET 2 YELLOW BLINK")
        self.close_sensor(new_sensor, actuator)

    def test_actuator_absent_and_back(self):
        """RF7 (c): the server works without actuator; a new one gets state."""
        first_row = len(server_log())
        actuator = self.register_actuator()
        # The actuator leaves; a moment later a reading changes the zone.
        actuator.close()
        time.sleep(SILENCE_S)
        sensor = self.connect("SENSOR")
        sensor.send("POST 1 10.0")
        self.wait_for_row(first_row, "DISCONNECT", value="ACTUATOR/closed")
        self.wait_for_row(first_row, "NO_ACTUATOR", seq="1")
        # A new actuator receives the zone that was decided without it.
        actuator = self.register_actuator("RED BLINK")
        sensor.send("POST 2 30.0")
        self.expect_set(actuator, "SET 2 YELLOW BLINK")
        self.close_sensor(sensor, actuator)

    def test_actuator_replaced(self):
        """RF7 (c): a new actuator replaces the old one and gets the state."""
        old_actuator = self.register_actuator()
        sensor = self.connect("SENSOR")
        sensor.send("POST 1 30.0")
        self.expect_set(old_actuator, "SET 1 YELLOW BLINK")
        # The new actuator first receives the current zone, MEDIUM.
        new_actuator = self.register_actuator("YELLOW BLINK")
        sensor.send("POST 2 10.0")
        self.expect_set(new_actuator, "SET 2 RED BLINK")
        # Commands only go to the actuator that registered last.
        self.assertIsNone(old_actuator.receive(SILENCE_S))
        # The replaced actuator is no longer registered: its ACK is rejected.
        old_actuator.send("ACK 2")
        self.assertEqual(old_actuator.receive(SILENCE_S),
                         "ERROR NOT_REGISTERED")
        self.close_sensor(sensor, new_actuator)

    def test_send_failure(self):
        """A SET that cannot be sent leaves the server without actuator.

        A failed send cannot be caused at will through the network, so this
        case runs a ControlServer in this process, with a closed socket as
        actuator and its log in a temporary folder.
        """
        # The temporary folder is deleted at the end, and the console output
        # of this second server is hidden.
        with tempfile.TemporaryDirectory() as folder, \
                contextlib.redirect_stdout(io.StringIO()):
            server = ControlServer(EventLog(Path(folder)))
            # Sending on a closed socket always fails.
            broken = socket.socket()
            broken.close()
            server.actuator = broken
            # The method that handles a POST, called without the network.
            server._on_post(["1", "10.0"])  # noqa: SLF001
            # The CSV of this server must show the failed send.
            with server.log.path.open(newline="", encoding="utf-8") as file:
                events = [row["event"] for row in csv.DictReader(file)]
        self.assertIsNone(server.actuator)
        self.assertIn("SEND_FAILED", events)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite,
               pattern: str | None) -> unittest.TestSuite:
    """Run the test classes in the order of the test plan."""
    del tests, pattern  # The order below replaces the default one.
    suite = unittest.TestSuite()
    for case in (ProtocolTest, ControlTest, DisconnectionTest):
        suite.addTests(loader.loadTestsFromTestCase(case))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)