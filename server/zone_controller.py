"""Control algorithm: turns each distance reading into a zone.

The module only does calculations; it has no network or hardware code.
"""

import math
from enum import Enum

import config


class Zone(Enum):
    """States of the control algorithm."""

    NEAR = "NEAR"
    MEDIUM = "MEDIUM"
    FAR = "FAR"
    ERROR = "ERROR"


# Command sent to the actuator for each zone, as "<led> <mode>".
ACTUATOR_COMMANDS = {
    Zone.NEAR: "RED BLINK",
    Zone.MEDIUM: "YELLOW BLINK",
    Zone.FAR: "WHITE ON",
    Zone.ERROR: "ALL BLINK",
}

# Readings that change the zone: each boundary moved HYSTERESIS_CM in the
# direction of the movement.
NEAR_TO_MEDIUM_CM = config.NEAR_MEDIUM_BOUNDARY_CM + config.HYSTERESIS_CM
MEDIUM_TO_NEAR_CM = config.NEAR_MEDIUM_BOUNDARY_CM - config.HYSTERESIS_CM
MEDIUM_TO_FAR_CM = config.MEDIUM_FAR_BOUNDARY_CM + config.HYSTERESIS_CM
FAR_TO_MEDIUM_CM = config.MEDIUM_FAR_BOUNDARY_CM - config.HYSTERESIS_CM


def is_valid(distance_cm: float) -> bool:
    """Return True if the reading is a number inside the sensor range."""
    return (math.isfinite(distance_cm)
            and config.MIN_VALID_CM <= distance_cm <= config.MAX_VALID_CM)


def classify(distance_cm: float) -> Zone:
    """Return the zone of one reading, without hysteresis.

    The ranges are contiguous and do not overlap, so every valid reading
    belongs to exactly one zone.
    """
    if not is_valid(distance_cm):
        return Zone.ERROR
    if distance_cm < config.NEAR_MEDIUM_BOUNDARY_CM:
        return Zone.NEAR
    if distance_cm < config.MEDIUM_FAR_BOUNDARY_CM:
        return Zone.MEDIUM
    return Zone.FAR


class ZoneController:
    """State machine that turns distance readings into a stable zone.

    - Hysteresis: the zone only changes when a reading passes a boundary
      by at least HYSTERESIS_CM, so a trembling object does not make the
      LEDs flicker.
    - Fault tolerance: isolated invalid readings keep the current zone;
      MAX_INVALID_READINGS invalid readings in a row change to ERROR.
    """

    def __init__(self) -> None:
        """Start in ERROR, because there is no reading yet."""
        self.zone = Zone.ERROR
        self._invalid_count = 0

    def update(self, distance_cm: float) -> bool:
        """Process one reading and return True if the zone changed."""
        if is_valid(distance_cm):
            # A valid reading ends any run of invalid readings.
            self._invalid_count = 0
            new_zone = self._next_zone(distance_cm)
        else:
            # Isolated invalid readings keep the zone and its hysteresis.
            self._invalid_count += 1
            if self._invalid_count < config.MAX_INVALID_READINGS:
                return False
            new_zone = Zone.ERROR
        # The caller only sends a command when the zone really changes.
        changed = new_zone != self.zone
        self.zone = new_zone
        return changed

    def reset(self) -> bool:
        """Change to ERROR, for example when the sensor disconnects.

        Return True if the zone changed.
        """
        changed = self.zone != Zone.ERROR
        self.zone = Zone.ERROR
        self._invalid_count = 0
        return changed

    def _next_zone(self, distance_cm: float) -> Zone:
        """Return the zone that follows the current one for a valid reading.

        Each zone is left only through its own thresholds. From ERROR the
        reading is classified directly, because there is no zone to leave.
        """
        # From NEAR the reading must go past the upper thresholds.
        if self.zone == Zone.NEAR:
            if distance_cm >= MEDIUM_TO_FAR_CM:
                return Zone.FAR
            if distance_cm >= NEAR_TO_MEDIUM_CM:
                return Zone.MEDIUM
            return Zone.NEAR
        # From MEDIUM it can leave downwards (NEAR) or upwards (FAR).
        if self.zone == Zone.MEDIUM:
            if distance_cm < MEDIUM_TO_NEAR_CM:
                return Zone.NEAR
            if distance_cm >= MEDIUM_TO_FAR_CM:
                return Zone.FAR
            return Zone.MEDIUM
        # From FAR the reading must go below the lower thresholds.
        if self.zone == Zone.FAR:
            if distance_cm < MEDIUM_TO_NEAR_CM:
                return Zone.NEAR
            if distance_cm < FAR_TO_MEDIUM_CM:
                return Zone.MEDIUM
            return Zone.FAR
        return classify(distance_cm)
