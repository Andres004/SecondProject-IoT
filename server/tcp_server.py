"""TCP control server of the system.

It receives the readings of the sensor, runs the control algorithm and
sends the commands to the actuator. Every event is logged with its t_ms.
"""

import csv
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

import config
from zone_controller import ACTUATOR_COMMANDS, ZoneController

ROLES = ("SENSOR", "ACTUATOR")  # Roles that a client can register.


def local_ip() -> str:
    """Return the IP address of this PC in the local network.

    Connecting a UDP socket only chooses the network route; no data is sent.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(config.IP_PROBE_ADDRESS)
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


class EventLog:
    """Writes every event with its t_ms on the console and in a CSV file.

    t_ms is the time in milliseconds since the server started. All events
    use this same clock, so the difference between two t_ms values is the
    time that passed between both events.
    """

    def __init__(self, folder: Path) -> None:
        """Create the CSV file with its header row and start the clock."""
        folder.mkdir(exist_ok=True)
        self.path = folder / datetime.now().strftime(
            "server_%Y%m%d_%H%M%S.csv")
        with open(self.path, "w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, config.LOG_COLUMNS).writeheader()
        self._start = time.perf_counter()
        self._lock = threading.Lock()

    def now_ms(self) -> float:
        """Return the current t_ms, rounded to 0.1 ms."""
        return round((time.perf_counter() - self._start) * 1000, 1)

    def write(self, event: str, t_ms: float | None = None,
              **fields) -> None:
        """Write one event; t_ms is the current time unless it is given.

        fields fills the optional columns: seq, value, zone, latency_ms.
        """
        if t_ms is None:
            t_ms = self.now_ms()
        details = " ".join(f"{name}={field}"
                           for name, field in fields.items())
        with self._lock:
            # Opening the file for each event keeps every event saved,
            # even if the program stops suddenly.
            with open(self.path, "a", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, config.LOG_COLUMNS).writerow(
                    {"t_ms": t_ms, "event": event, **fields})
            print(f"[t_ms={t_ms:>9.1f}] {event:<14} {details}")


class ControlServer:
    """Central control entity of the system.

    Each client is served by its own thread. One lock protects the state
    that the threads share: the controller, the registered clients and the
    commands waiting for their ACK.
    """

    def __init__(self, log: EventLog) -> None:
        """Start without clients and with the controller in ERROR."""
        self.log = log
        self.controller = ZoneController()
        self.sensor: socket.socket | None = None
        self.actuator: socket.socket | None = None
        self.pending: dict[int, float] = {}  # seq -> t_ms of what caused it
        self.lock = threading.Lock()

    def serve_forever(self) -> None:
        """Accept clients until Ctrl+C."""
        with socket.create_server((config.HOST, config.PORT)) as listener:
            listener.settimeout(config.ACCEPT_TIMEOUT_S)
            self.log.write("START", value=f"{local_ip()}:{config.PORT}")
            while True:
                try:
                    conn, address = listener.accept()
                except TimeoutError:
                    continue
                # TCP_NODELAY sends each short message at once.
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # Reading a socket blocks, so each client has its own thread.
                threading.Thread(target=self._serve_client,
                                 args=(conn, address), daemon=True).start()

    def _serve_client(self, conn: socket.socket, address: tuple) -> None:
        """Read the messages of one client until it disconnects."""
        self.log.write("CONNECT", value=f"{address[0]}:{address[1]}")
        role, reason = None, "closed"
        try:
            # makefile() splits the TCP byte stream into lines ended by '\n'.
            with conn, conn.makefile("r", encoding="ascii",
                                     errors="replace") as reader:
                for line in reader:
                    role = self._handle_line(conn, role, line.strip())
        except TimeoutError:
            reason = "timeout"
        except OSError:
            reason = "error"
        self._on_disconnect(conn, role, reason)

    def _handle_line(self, conn: socket.socket, role: str | None,
                     line: str) -> str | None:
        """Process one message and return the role of the client.

        Only the registered sensor may send POST and only the registered
        actuator may send ACK. A connection replaced by a newer REGISTER
        of the same role is no longer registered.
        """
        # Empty or too long lines are not valid messages.
        parts = line.split()
        if not parts or len(line) > config.MAX_LINE_LENGTH:
            self._reject(conn, "BAD_FORMAT", line)
            return role
        command, args = parts[0], parts[1:]
        # Wrong arguments (missing, extra or not numeric) raise ValueError.
        try:
            if command == "REGISTER":
                return self._on_register(conn, args)
            if role is None or not self._is_current(conn, role):
                self._reject(conn, "NOT_REGISTERED", line)
            elif command == "POST" and role == "SENSOR":
                self._on_post(args)
            elif command == "ACK" and role == "ACTUATOR":
                self._on_ack(args)
            else:
                self._reject(conn, "UNKNOWN_CMD", line)
        except ValueError:
            self._reject(conn, "BAD_FORMAT", line)
        return role

    def _is_current(self, conn: socket.socket, role: str) -> bool:
        """Return True if conn is the client registered now with role."""
        with self.lock:
            current = self.sensor if role == "SENSOR" else self.actuator
            return conn is current

    def _on_register(self, conn: socket.socket, args: list[str]) -> str:
        """REGISTER <role>: save the client under its role.

        If another client had that role, this client takes its place.
        """
        (role,) = args
        if role not in ROLES:
            raise ValueError(role)
        with self.lock:
            self._send(conn, "OK")
            self.log.write("REGISTER", value=role)
            if role == "SENSOR":
                # The sensor must send something at least every
                # SENSOR_TIMEOUT_S, or it is considered lost.
                conn.settimeout(config.SENSOR_TIMEOUT_S)
                self.sensor = conn
            else:
                # The actuator receives the current state at once.
                self.actuator = conn
                self._send_command(0, self.log.now_ms())
        return role

    def _on_post(self, args: list[str]) -> None:
        """POST <seq> <cm>: run the control algorithm on one reading."""
        seq_text, distance_text = args
        seq, distance = int(seq_text), float(distance_text)
        with self.lock:
            # t_post is the start of the latency measured for this reading.
            t_post = self.log.now_ms()
            changed = self.controller.update(distance)
            self.log.write("POST", t_post, seq=seq, value=distance_text,
                           zone=self.controller.zone.name)
            # A command is sent only when the zone changes.
            if changed:
                self._send_command(seq, t_post)

    def _on_ack(self, args: list[str]) -> None:
        """ACK <seq>: the actuator applied a command; log its latency.

        The latency is the time from the event that caused the command to
        the arrival of this ACK.
        """
        (seq_text,) = args
        seq = int(seq_text)
        with self.lock:
            t_ack = self.log.now_ms()
            t_cause = self.pending.pop(seq, None)
            latency = "" if t_cause is None else round(t_ack - t_cause, 1)
            self.log.write("ACK", t_ack, seq=seq, latency_ms=latency)

    def _on_disconnect(self, conn: socket.socket, role: str | None,
                       reason: str) -> None:
        """Forget a client that left; losing the sensor commands ERROR."""
        with self.lock:
            self.log.write("DISCONNECT",
                           value=f"{role or 'UNREGISTERED'}/{reason}")
            # The comparison ignores an old connection that was replaced.
            if conn is self.actuator:
                self.actuator = None
            if conn is self.sensor:
                self.sensor = None
                if self.controller.reset():
                    self._send_command(0, self.log.now_ms())

    def _send_command(self, seq: int, t_cause: float) -> None:
        """Send the command of the current zone to the actuator.

        The caller must hold the lock. t_cause is the t_ms of the event that
        caused the command; the latency of its ACK is measured from it.
        """
        zone = self.controller.zone
        command = ACTUATOR_COMMANDS[zone]
        if self.actuator is None:
            self.log.write("NO_ACTUATOR", seq=seq, value=command,
                           zone=zone.name)
            return
        # A failed send means the actuator is gone; it must register again.
        try:
            self._send(self.actuator, f"SET {seq} {command}")
        except OSError:
            self.actuator = None
            self.log.write("SEND_FAILED", seq=seq, value=command)
            return
        # The command waits in pending until its ACK arrives.
        self.pending[seq] = t_cause
        self.log.write("SET", seq=seq, value=command, zone=zone.name)

    def _reject(self, conn: socket.socket, code: str, line: str) -> None:
        """Answer an invalid message with ERROR <code>."""
        with self.lock:
            self._send(conn, f"ERROR {code}")
            self.log.write("PROTOCOL_ERROR",
                           value=f"{code}: {line[:config.MAX_LINE_LENGTH]}")

    @staticmethod
    def _send(conn: socket.socket, message: str) -> None:
        """Send one message followed by a newline."""
        conn.sendall((message + "\n").encode("ascii"))


def main() -> None:
    """Start the server; Ctrl+C stops it."""
    log = EventLog(config.LOG_DIR)
    print(f"Logging to {log.path}")
    try:
        ControlServer(log).serve_forever()
    except KeyboardInterrupt:
        log.write("STOP")


if __name__ == "__main__":
    main()
