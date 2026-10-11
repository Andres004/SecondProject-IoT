"""TCP control server: receives sensor readings and commands the actuator.

Run from the repository root:
    python server/tcp_server.py
"""

import csv
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

import config
from zone_controller import ACTUATOR_COMMANDS, ZoneController

ROLES = ("SENSOR", "ACTUATOR")


def local_ip() -> str:
    """Return the LAN IP of this PC (the value for SERVER_HOST).

    Connecting a UDP socket only selects the network route; no data is sent.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(config.IP_PROBE_ADDRESS)
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


class EventLog:
    """Records every event with its t_ms on the console and in a CSV file.

    t_ms is the time in milliseconds since the server started. All
    timestamps come from this single clock, so latencies can be computed
    by subtracting them.
    """

    def __init__(self, folder: Path) -> None:
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
        """Record one event; t_ms defaults to the current time.

        fields fills the optional columns: seq, value, zone, latency_ms.
        """
        if t_ms is None:
            t_ms = self.now_ms()
        details = " ".join(f"{name}={field}"
                           for name, field in fields.items())
        with self._lock:
            with open(self.path, "a", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, config.LOG_COLUMNS).writerow(
                    {"t_ms": t_ms, "event": event, **fields})
            print(f"[t_ms={t_ms:>9.1f}] {event:<14} {details}")


class ControlServer:
    """Central control entity of the system.

    Each TCP client is served by its own thread. Shared state (the
    controller and the registered clients) is protected by one lock.
    """

    def __init__(self, log: EventLog) -> None:
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
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                threading.Thread(target=self._serve_client,
                                 args=(conn, address), daemon=True).start()

    def _serve_client(self, conn: socket.socket, address: tuple) -> None:
        """Read protocol lines from one client until it disconnects."""
        self.log.write("CONNECT", value=f"{address[0]}:{address[1]}")
        role, reason = None, "closed"
        try:
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
        """Process one protocol message and return the client's role."""
        parts = line.split()
        if not parts or len(line) > config.MAX_LINE_LENGTH:
            self._reject(conn, "BAD_FORMAT", line)
            return role
        command, args = parts[0], parts[1:]
        try:
            if command == "REGISTER":
                return self._on_register(conn, args)
            if role is None:
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

    def _on_register(self, conn: socket.socket, args: list[str]) -> str:
        """REGISTER <role>: a new client replaces the previous one."""
        (role,) = args
        if role not in ROLES:
            raise ValueError(role)
        with self.lock:
            self._send(conn, "OK")
            self.log.write("REGISTER", value=role)
            if role == "SENSOR":
                conn.settimeout(config.SENSOR_TIMEOUT_S)
                self.sensor = conn
            else:
                self.actuator = conn
                self._send_command(0, self.log.now_ms())
        return role

    def _on_post(self, args: list[str]) -> None:
        """POST <seq> <cm>: run the control algorithm on one reading."""
        seq_text, distance_text = args
        seq, distance = int(seq_text), float(distance_text)
        with self.lock:
            t_post = self.log.now_ms()
            changed = self.controller.update(distance)
            self.log.write("POST", t_post, seq=seq, value=distance_text,
                           zone=self.controller.zone.name)
            if changed:
                self._send_command(seq, t_post)

    def _on_ack(self, args: list[str]) -> None:
        """ACK <seq>: the actuator applied the command; log the latency."""
        (seq_text,) = args
        seq = int(seq_text)
        with self.lock:
            t_ack = self.log.now_ms()
            t_cause = self.pending.pop(seq, None)
            latency = "" if t_cause is None else round(t_ack - t_cause, 1)
            self.log.write("ACK", t_ack, seq=seq, latency_ms=latency)

    def _on_disconnect(self, conn: socket.socket, role: str | None,
                       reason: str) -> None:
        """Forget the client; losing the sensor commands ERROR."""
        with self.lock:
            self.log.write("DISCONNECT",
                           value=f"{role or 'UNREGISTERED'}/{reason}")
            if conn is self.actuator:
                self.actuator = None
            if conn is self.sensor:
                self.sensor = None
                if self.controller.reset():
                    self._send_command(0, self.log.now_ms())

    def _send_command(self, seq: int, t_cause: float) -> None:
        """Send the command of the current zone (the lock must be held).

        t_cause is the t_ms of the event that caused the command; the ACK
        latency is measured from it.
        """
        zone = self.controller.zone
        command = ACTUATOR_COMMANDS[zone]
        if self.actuator is None:
            self.log.write("NO_ACTUATOR", seq=seq, value=command,
                           zone=zone.name)
            return
        try:
            self._send(self.actuator, f"SET {seq} {command}")
        except OSError:
            self.actuator = None
            self.log.write("SEND_FAILED", seq=seq, value=command)
            return
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
        """Send one protocol message terminated by a newline."""
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
