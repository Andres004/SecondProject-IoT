"""Measures the requirements from the logs of a test run.

Usage, from the server folder:
    python -m tests.analyze_log [FILE ...] [REF_CM:FIRST_SEQ ...]

FILE is a CSV log of the server (logs/server_*.csv) or a log of the serial
monitor of an ESP32 (platformio-device-monitor-*.log). Without files it uses
the newest CSV in logs/. A file name may use * to select several files, for
example logs/server_*.csv. Each REF_CM:FIRST_SEQ pair compares the ten
readings that start at FIRST_SEQ with the distance REF_CM measured with a
tape. Each result line starts with the requirement it measures and ends
with PASS, FAIL or NOT ENOUGH DATA.
"""

import csv
import glob
import math
import re
import statistics
import sys
from itertools import pairwise
from pathlib import Path

import config
from zone_controller import ZoneController, is_valid

# Acceptance values of the requirements.
MIN_RUN_MS = 600_000  # RNF1: the stability run lasts at least 10 min.
MAX_GAP_MS = 1000  # RNF1: a longer pause between two readings is a block.
WINDOW_MS = 10_000  # RNF4: readings are counted in windows of 10 s.
MIN_READINGS_PER_WINDOW = 50  # RNF4: at least 5 readings per second.
SAMPLE_PERIOD_MS = 100  # OI-1 period: longest wait for the next reading.
MAX_RESPONSE_MS = 1000  # RNF3: worst response time.
MIN_ZONE_CHANGES = 10  # RNF3: zone changes needed for the measurement.
MAX_FAILSAFE_MS = 1500  # RF7 (a): from the last reading to ACK 0.
MAX_RECONNECT_MS = 3000  # RNF5: from START to the REGISTER of each client.
ACCURACY_READINGS = 10  # RNF2: readings compared with each reference.
MAX_ERROR_CM = 3.0  # RNF2: largest error of a single reading.
ACCURACY_MIN_CM = 5.0  # RNF2: shortest distance of the accuracy range.
ACCURACY_MAX_CM = 100.0  # RNF2: longest distance of the accuracy range.
RETRY_INTERVAL_MS = 2000  # RF7 (c): time between two connection attempts.
WIFI_RETRY_INTERVAL_MS = 10_000  # RF7 (c): time between two WiFi requests.
RETRY_TOLERANCE_MS = 300  # Connection wait (250 ms) plus loop delays.

READING_FORMAT = re.compile(r"\d+\.\d|NAN")  # RF1: one decimal, or NAN.
DEVICE_LINE = re.compile(r"\[t_ms=\s*(\d+)\]\s+(\S+)\s*(.*)")  # ESP32 log.
COMMAND_EVENTS = ("SET", "NO_ACTUATOR", "SEND_FAILED")  # A command result.
COMMAND_SEARCH_ROWS = 3  # Rows after a reading where its command is logged.
MAX_LISTED_CHANGES = 20  # Zone changes printed one by one.


def verdict(passed: bool, enough_data: bool = True) -> str:
    """Return the word that ends each result line."""
    if not passed:
        return "FAIL"
    return "PASS" if enough_data else "NOT ENOUGH DATA"


def percentile(values: list[float], fraction: float) -> float:
    """Return the value below which lies that fraction of the values."""
    # Nearest-rank method: sort and take the value at that position.
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def load(path: Path) -> list[dict]:
    """Read the rows of one CSV log, with t_ms and seq as numbers."""
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    # The CSV module reads every field as text; times and seq become numbers.
    for row in rows:
        row["t_ms"] = float(row["t_ms"])
        row["seq"] = int(row["seq"]) if row["seq"] else None
    return rows


def report_readings(rows: list[dict], posts: list[dict]) -> None:
    """RNF1 and RNF4: rate, pauses, lost readings and restarts of OI-1."""
    if len(posts) < 2:
        print("Readings: fewer than two, nothing to measure")
        return
    # Time of each reading and pause between two consecutive readings.
    times = [row["t_ms"] for row in posts]
    gaps = [after - before for before, after in pairwise(times)]
    # seq grows by one per reading: a jump means lost readings and a step
    # back means that OI-1 restarted.
    steps = [after["seq"] - before["seq"]
             for before, after in pairwise(posts)]
    lost = sum(step - 1 for step in steps if step > 1)
    restarts = sum(step <= 0 for step in steps)
    invalid = sum(not is_valid(float(row["value"])) for row in posts)
    disconnects = sum(row["event"] == "DISCONNECT" for row in rows)
    span = times[-1] - times[0]
    print(f"Readings: {len(posts)} received over {span / 60000:.1f} min, "
          f"{invalid} invalid, {lost} lost, {restarts} seq restarts")
    # OI-1 writes each distance with one decimal, or NAN if it is invalid.
    badly_written = sum(not READING_FORMAT.fullmatch(row["value"])
                        for row in posts)
    print(f"RF1 format: {badly_written} readings without one decimal or NAN"
          f" -> {verdict(badly_written == 0)}")

    # The readings are counted in consecutive windows of 10 s. Only whole
    # windows are counted, so a short last piece does not lower the result.
    counts = []
    start = times[0]
    while start + WINDOW_MS <= times[-1]:
        counts.append(sum(start <= t < start + WINDOW_MS for t in times))
        start += WINDOW_MS
    if counts:
        print(f"RNF4 readings per 10 s window: min {min(counts)}, "
              f"mean {statistics.mean(counts):.1f}, max {max(counts)} -> "
              f"{verdict(min(counts) >= MIN_READINGS_PER_WINDOW)}")

    # Stable: no long pause, no restart of OI-1 and no lost connection.
    stable = max(gaps) < MAX_GAP_MS and restarts == 0 and disconnects == 0
    print(f"RNF1 time between readings: mean {statistics.mean(gaps):.1f} ms,"
          f" p95 {percentile(gaps, 0.95):.1f} ms, max {max(gaps):.1f} ms; "
          f"{disconnects} disconnections -> "
          f"{verdict(stable, span >= MIN_RUN_MS)}")


def has_command(rows: list[dict], index: int) -> bool:
    """Tell if the reading at index has its command in the next rows."""
    # The server logs the command right after the reading that caused it.
    following = rows[index + 1:index + 1 + COMMAND_SEARCH_ROWS]
    return any(row["event"] in COMMAND_EVENTS
               and row["seq"] == rows[index]["seq"] for row in following)


def report_control(rows: list[dict]) -> None:
    """RF2, RF5, RF6: replay the readings through the control algorithm.

    The zone logged with each reading must be the one that ZoneController
    gives, and each zone change must have its command, with no others.
    """
    # A fresh controller starts in ERROR, like the server when it starts.
    controller = ZoneController()
    wrong_zones = 0
    changes: list[str] = []
    without_command = 0
    first_invalid_ms = None  # t_ms of the first of the invalid readings.
    for index, row in enumerate(rows):
        # Like the server, losing the sensor puts the zone in ERROR.
        if row["event"] == "DISCONNECT" and row["value"].startswith("SENSOR"):
            controller.reset()
        if row["event"] != "POST":
            continue
        # Remember when the current run of invalid readings started.
        distance = float(row["value"])
        if is_valid(distance):
            first_invalid_ms = None
        elif first_invalid_ms is None:
            first_invalid_ms = row["t_ms"]
        # The same reading goes through the algorithm, and its zone must be
        # the one that the server logged.
        before = controller.zone
        changed = controller.update(distance)
        wrong_zones += controller.zone.name != row["zone"]
        if not changed:
            continue
        change = (f"seq {row['seq']} {row['value']}: {before.name} -> "
                  f"{controller.zone.name}")
        if first_invalid_ms is not None:
            change += (f" ({row['t_ms'] - first_invalid_ms:.0f} ms after "
                       "the first invalid reading)")
        changes.append(change)
        without_command += not has_command(rows, index)
    # Commands caused by readings (seq > 0) that match no zone change.
    commands = sum(row["event"] in COMMAND_EVENTS and bool(row["seq"])
                   for row in rows)
    extra = commands - (len(changes) - without_command)
    passed = wrong_zones == 0 and without_command == 0 and extra == 0
    print(f"RF2/RF5/RF6 control: {wrong_zones} zones different from the "
          f"algorithm, {len(changes)} zone changes, {without_command} without"
          f" command, {extra} extra commands -> {verdict(passed)}")
    for change in changes[:MAX_LISTED_CHANGES]:
        print(f"     {change}")
    if len(changes) > MAX_LISTED_CHANGES:
        print(f"     ... and {len(changes) - MAX_LISTED_CHANGES} more")


def report_response(rows: list[dict]) -> None:
    """RNF3: response time of each zone change caused by a reading."""
    # ACK 0 is left out: it answers a command that no reading caused.
    latencies = [float(row["latency_ms"]) for row in rows
                 if row["event"] == "ACK" and row["seq"]
                 and row["latency_ms"]]
    if not latencies:
        return
    # Worst case: the change happens right after a reading, so OI-1 needs
    # up to one period to measure it, and then the latency of the chain.
    worst = SAMPLE_PERIOD_MS + max(latencies)
    result = verdict(worst <= MAX_RESPONSE_MS,
                     len(latencies) >= MIN_ZONE_CHANGES)
    print(f"RNF3 latency_ms of {len(latencies)} zone changes: "
          f"min {min(latencies):.1f}, "
          f"median {statistics.median(latencies):.1f}, "
          f"p95 {percentile(latencies, 0.95):.1f}, max {max(latencies):.1f}; "
          f"worst response {SAMPLE_PERIOD_MS} + {max(latencies):.1f} = "
          f"{worst:.1f} ms -> {result}")
    print("     each change: "
          + ", ".join(f"{latency:.1f}" for latency in latencies))


def report_sensor_loss(rows: list[dict]) -> None:
    """RF7 (a): time from the last reading to the ACK of the ERROR."""
    last_post = None
    for index, row in enumerate(rows):
        if row["event"] == "POST":
            last_post = row
        # Only the loss of the sensor after at least one reading is measured.
        if (row["event"] != "DISCONNECT" or last_post is None
                or not row["value"].startswith("SENSOR/")):
            continue
        # The ACK 0 that follows, before the sensor sends again.
        ack = None
        for later in rows[index + 1:]:
            if later["event"] == "POST":
                break
            if later["event"] == "ACK" and later["seq"] == 0:
                ack = later
                break
        lost_after = row["t_ms"] - last_post["t_ms"]
        if ack is None:
            print(f"RF7 (a) sensor lost ({row['value']}) {lost_after:.0f} ms "
                  "after the last reading; no ACK 0 (zone already ERROR "
                  "or no actuator)")
        else:
            acked_after = ack["t_ms"] - last_post["t_ms"]
            print(f"RF7 (a) sensor lost ({row['value']}) {lost_after:.0f} "
                  f"ms after the last reading; ACK 0 after "
                  f"{acked_after:.0f} ms -> "
                  f"{verdict(acked_after <= MAX_FAILSAFE_MS)}")
        last_post = None  # The next loss is measured from a new reading.


def report_reconnection(rows: list[dict]) -> None:
    """RNF5: time from START to the first REGISTER of each client.

    It only measures a reconnection when the clients were already running
    before the server started, as after a restart of the server.
    """
    start = next((row for row in rows if row["event"] == "START"), None)
    if start is None:
        return
    for role in ("SENSOR", "ACTUATOR"):
        register = next((row for row in rows if row["event"] == "REGISTER"
                         and row["value"] == role), None)
        if register is not None:
            delay = register["t_ms"] - start["t_ms"]
            print(f"RNF5 after a server restart: REGISTER {role} "
                  f"{delay:.0f} ms after START -> "
                  f"{verdict(delay <= MAX_RECONNECT_MS)}")


def report_protocol(rows: list[dict]) -> None:
    """RF4: protocol errors and commands without their ACK."""
    errors = sum(row["event"] == "PROTOCOL_ERROR" for row in rows)
    waiting: dict[int, int] = {}  # seq -> SET commands still without ACK
    unexpected_acks = 0
    # Each SET waits for an ACK with its seq; an ACK with no SET waiting is
    # unexpected.
    for row in rows:
        if row["event"] == "SET":
            waiting[row["seq"]] = waiting.get(row["seq"], 0) + 1
        elif row["event"] == "ACK":
            if waiting.get(row["seq"]):
                waiting[row["seq"]] -= 1
            else:
                unexpected_acks += 1
    missing = sum(waiting.values())
    passed = errors == 0 and missing == 0 and unexpected_acks == 0
    print(f"RF4 protocol: {errors} PROTOCOL_ERROR, {missing} SET without "
          f"ACK, {unexpected_acks} ACK without SET -> {verdict(passed)}")


def report_accuracy(posts: list[dict], ref_cm: float, first: int) -> None:
    """RNF2: compare ACCURACY_READINGS readings with a tape distance.

    Outside the accuracy range of RNF2 (5 to 100 cm) the error is only
    reported, and the result checks RF2: every reading must be valid.
    """
    in_range = ACCURACY_MIN_CM <= ref_cm <= ACCURACY_MAX_CM
    label = "RNF2" if in_range else "RF2 range limit"
    last = first + ACCURACY_READINGS - 1
    # The readings from FIRST_SEQ to LAST, taken while the target was still.
    readings: dict[int, float] = {}
    for row in posts:
        if first <= row["seq"] <= last:
            readings.setdefault(row["seq"], float(row["value"]))
    values = [value for value in readings.values() if is_valid(value)]
    invalid = len(readings) - len(values)
    if not values:
        print(f"{label} {ref_cm:.1f} cm, seq {first}-{last}: "
              f"{len(readings)} readings in this log, none valid -> FAIL")
        return
    # Error of each reading against the tape, and the spread of the readings.
    errors = [abs(value - ref_cm) for value in values]
    mean = statistics.mean(values)
    spread = max(values) - min(values)
    passed = len(values) == ACCURACY_READINGS and (
        max(errors) <= MAX_ERROR_CM or not in_range)
    print(f"{label} {ref_cm:.1f} cm, seq {first}-{last}: {len(values)} valid, "
          f"{invalid} invalid, min {min(values):.1f}, max {max(values):.1f}, "
          f"mean {mean:.2f}, max error {max(errors):.1f}, "
          f"error of mean {abs(mean - ref_cm):.2f}, spread {spread:.1f} cm"
          f" -> {verdict(passed)}")


def analyze(path: Path, references: list[tuple[float, int]]) -> None:
    """Print every measurement that the log of one server run allows."""
    rows = load(path)
    if not rows:
        print(f"\n== {path.name}: empty")
        return
    posts = [row for row in rows if row["event"] == "POST"]
    duration = rows[-1]["t_ms"] - rows[0]["t_ms"]
    print(f"\n== {path.name} ({duration / 1000:.1f} s, {len(rows)} events)")
    report_readings(rows, posts)
    report_control(rows)
    report_response(rows)
    report_sensor_loss(rows)
    report_reconnection(rows)
    report_protocol(rows)
    for ref_cm, first in references:
        report_accuracy(posts, ref_cm, first)


def report_intervals(label: str, times: list[list[int]], interval: int,
                     ) -> None:
    """Check the time between retries; each inner list is one outage."""
    gaps = [after - before for outage in times
            for before, after in pairwise(outage)]
    if gaps:
        passed = all(abs(gap - interval) <= RETRY_TOLERANCE_MS
                     for gap in gaps)
        print(f"RF7 (c) {label} every {min(gaps)} to {max(gaps)} ms "
              f"({len(gaps)} intervals) -> {verdict(passed)}")


def analyze_device(path: Path) -> None:
    """Print the measurements that the log of one ESP32 allows."""
    # Each log line looks like "[t_ms=   1234] EVENT details".
    events = []
    with path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            match = DEVICE_LINE.search(line)
            if match:
                events.append((int(match[1]), match[2], match[3].strip()))
    print(f"\n== {path.name} ({len(events)} events)")
    if not events:
        return
    # How many times each important event appears.
    names = [name for _, name, _ in events]
    print("Events: " + ", ".join(
        f"{name} {names.count(name)}" for name in (
            "BOOT", "SERVER_CONNECTED", "SERVER_LOST", "SERVER_UNREACHABLE",
            "WIFI_RETRY", "TX_FAILED", "RX_TOO_LONG")))
    for _, name, details in events:
        if name == "SERVER_LOST":
            print(f"     SERVER_LOST {details}")
    # A BOOT after the first line means that the board restarted.
    restarts = names[1:].count("BOOT")
    print(f"RNF1 restarts: {restarts} -> {verdict(restarts == 0)}")

    # Retries are measured inside each outage: a new outage starts when the
    # board connects again or loses the server.
    attempts: list[list[int]] = [[]]
    wifi_requests: list[list[int]] = [[]]
    for t_ms, name, _ in events:
        if name in ("SERVER_UNREACHABLE", "SERVER_CONNECTED"):
            attempts[-1].append(t_ms)
            wifi_requests.append([])  # An attempt means the WiFi was up.
        if name == "WIFI_RETRY":
            wifi_requests[-1].append(t_ms)
        if name in ("SERVER_CONNECTED", "SERVER_LOST", "BOOT"):
            attempts.append([])
    report_intervals("connection attempts", attempts, RETRY_INTERVAL_MS)
    report_intervals("WiFi requests", wifi_requests, WIFI_RETRY_INTERVAL_MS)


def main() -> None:
    """Split the arguments into files and references and analyze each file."""
    files: list[str] = []
    references: list[tuple[float, int]] = []
    # Arguments ending in .csv, .log or .txt are files; the rest are pairs
    # REF_CM:FIRST_SEQ.
    for argument in sys.argv[1:]:
        if argument.lower().endswith((".csv", ".log", ".txt")):
            # Windows does not expand *, so glob does it here.
            files += sorted(glob.glob(argument)) or [argument]
        else:
            ref_cm, first = argument.split(":")
            references.append((float(ref_cm), int(first)))
    # Without files, the newest CSV: its name holds the date and time.
    if not files:
        files = sorted(str(path) for path in
                       config.LOG_DIR.glob("server_*.csv"))[-1:]
    if not files:
        print(f"No CSV files in {config.LOG_DIR}")
    # A CSV comes from the server; any other file is the log of an ESP32.
    for name in files:
        if name.lower().endswith(".csv"):
            analyze(Path(name), references)
        else:
            analyze_device(Path(name))


if __name__ == "__main__":
    main()
