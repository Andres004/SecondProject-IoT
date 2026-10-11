"""Control algorithm: distance classification with hysteresis.

This module is pure logic (no sockets, no hardware), so it can be unit
tested on any PC.
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


#: Actuator command for each zone, in the protocol format "<led> <mode>".
ACTUATOR_COMMANDS = {
    Zone.NEAR: "RED BLINK",
    Zone.MEDIUM: "YELLOW BLINK",
    Zone.FAR: "WHITE ON",
    Zone.ERROR: "ALL BLINK",
}

# A zone change requires passing the boundary by HYSTERESIS_CM.
NEAR_TO_MEDIUM_CM = config.NEAR_MEDIUM_BOUNDARY_CM + config.HYSTERESIS_CM
MEDIUM_TO_NEAR_CM = config.NEAR_MEDIUM_BOUNDARY_CM - config.HYSTERESIS_CM
MEDIUM_TO_FAR_CM = config.MEDIUM_FAR_BOUNDARY_CM + config.HYSTERESIS_CM
FAR_TO_MEDIUM_CM = config.MEDIUM_FAR_BOUNDARY_CM - config.HYSTERESIS_CM


def is_valid(distance_cm: float) -> bool:
    """Return True if the reading is a number inside the sensor range."""
    return (math.isfinite(distance_cm)
            and config.MIN_VALID_CM <= distance_cm <= config.MAX_VALID_CM)


def classify(distance_cm: float) -> Zone:
    """Classify one reading into contiguous, non-overlapping ranges.

    This is the plain classification (RF2), without hysteresis.
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
    - Fault tolerance: isolated invalid readings are ignored and keep the
      current zone; MAX_INVALID_READINGS in a row enter ERROR.
    """

    def __init__(self) -> None:
        self.zone = Zone.ERROR
        self._invalid_count = 0

    def update(self, distance_cm: float) -> bool:
        """Process one reading. Return True if the zone changed."""
        if is_valid(distance_cm):
            self._invalid_count = 0
            new_zone = self._next_zone(distance_cm)
        else:
            self._invalid_count += 1
            if self._invalid_count < config.MAX_INVALID_READINGS:
                return False
            new_zone = Zone.ERROR
        changed = new_zone != self.zone
        self.zone = new_zone
        return changed

    def reset(self) -> bool:
        """Enter ERROR, e.g. when the sensor disconnects.

        Return True if the zone changed.
        """
        changed = self.zone != Zone.ERROR
        self.zone = Zone.ERROR
        self._invalid_count = 0
        return changed

    def _next_zone(self, distance_cm: float) -> Zone:
        """Transition table of the state machine for a valid reading.

        From ERROR there is no previous zone, so the reading is
        classified directly.
        """
        if self.zone == Zone.NEAR:
            if distance_cm >= MEDIUM_TO_FAR_CM:
                return Zone.FAR
            if distance_cm >= NEAR_TO_MEDIUM_CM:
                return Zone.MEDIUM
            return Zone.NEAR
        if self.zone == Zone.MEDIUM:
            if distance_cm < MEDIUM_TO_NEAR_CM:
                return Zone.NEAR
            if distance_cm >= MEDIUM_TO_FAR_CM:
                return Zone.FAR
            return Zone.MEDIUM
        if self.zone == Zone.FAR:
            if distance_cm < MEDIUM_TO_NEAR_CM:
                return Zone.NEAR
            if distance_cm < FAR_TO_MEDIUM_CM:
                return Zone.MEDIUM
            return Zone.FAR
        return classify(distance_cm)
