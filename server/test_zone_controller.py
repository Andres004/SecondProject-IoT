"""Unit tests of the control algorithm (no network, no hardware).

Run from the repository root:
    python -m unittest discover -s server -v
"""

import math
import unittest

from zone_controller import ACTUATOR_COMMANDS, Zone, ZoneController, classify


def controller_in(first_reading: float) -> ZoneController:
    """Return a controller already placed in the zone of first_reading."""
    controller = ZoneController()
    controller.update(first_reading)
    return controller


class ClassifyTest(unittest.TestCase):
    """RF2: contiguous, non-overlapping ranges at their exact boundaries."""

    def test_blind_zone_boundary(self):
        self.assertEqual(classify(1.9), Zone.ERROR)
        self.assertEqual(classify(2.0), Zone.NEAR)

    def test_near_medium_boundary(self):
        self.assertEqual(classify(19.9), Zone.NEAR)
        self.assertEqual(classify(20.0), Zone.MEDIUM)

    def test_medium_far_boundary(self):
        self.assertEqual(classify(39.9), Zone.MEDIUM)
        self.assertEqual(classify(40.0), Zone.FAR)

    def test_max_range_boundary(self):
        self.assertEqual(classify(400.0), Zone.FAR)
        self.assertEqual(classify(400.1), Zone.ERROR)

    def test_non_numeric_readings(self):
        self.assertEqual(classify(math.nan), Zone.ERROR)
        self.assertEqual(classify(math.inf), Zone.ERROR)


class HysteresisTest(unittest.TestCase):
    """The zone changes only after passing a boundary by HYSTERESIS_CM."""

    def assert_transition(self, start, stay, change, expected):
        """From the zone of start, stay keeps it and change moves it."""
        controller = controller_in(start)
        initial_zone = controller.zone
        self.assertFalse(controller.update(stay))
        self.assertEqual(controller.zone, initial_zone)
        self.assertTrue(controller.update(change))
        self.assertEqual(controller.zone, expected)

    def test_near_to_medium(self):
        self.assert_transition(10.0, 21.9, 22.0, Zone.MEDIUM)

    def test_medium_to_near(self):
        self.assert_transition(30.0, 18.0, 17.9, Zone.NEAR)

    def test_medium_to_far(self):
        self.assert_transition(30.0, 41.9, 42.0, Zone.FAR)

    def test_far_to_medium(self):
        self.assert_transition(50.0, 38.0, 37.9, Zone.MEDIUM)

    def test_jump_near_to_far(self):
        self.assert_transition(10.0, 21.9, 42.0, Zone.FAR)

    def test_jump_far_to_near(self):
        self.assert_transition(50.0, 38.0, 17.9, Zone.NEAR)

    def test_first_reading_is_classified_directly(self):
        controller = ZoneController()
        self.assertEqual(controller.zone, Zone.ERROR)
        self.assertTrue(controller.update(20.0))
        self.assertEqual(controller.zone, Zone.MEDIUM)


class InvalidReadingTest(unittest.TestCase):
    """Isolated invalid readings are tolerated; a burst enters ERROR."""

    def test_two_invalid_readings_keep_zone_and_hysteresis(self):
        controller = controller_in(30.0)
        self.assertFalse(controller.update(math.nan))
        self.assertFalse(controller.update(math.nan))
        self.assertEqual(controller.zone, Zone.MEDIUM)
        self.assertFalse(controller.update(18.0))
        self.assertEqual(controller.zone, Zone.MEDIUM)

    def test_third_invalid_reading_enters_error(self):
        controller = controller_in(30.0)
        controller.update(math.nan)
        controller.update(math.nan)
        self.assertTrue(controller.update(math.nan))
        self.assertEqual(controller.zone, Zone.ERROR)

    def test_valid_reading_restarts_the_invalid_count(self):
        controller = controller_in(30.0)
        for reading in (math.nan, math.nan, 30.0, math.nan, math.nan):
            controller.update(reading)
        self.assertEqual(controller.zone, Zone.MEDIUM)

    def test_reset_enters_error(self):
        controller = controller_in(30.0)
        self.assertTrue(controller.reset())
        self.assertEqual(controller.zone, Zone.ERROR)
        self.assertFalse(controller.reset())


class CommandTest(unittest.TestCase):
    """RF3: every zone has its own actuator behaviour."""

    def test_every_zone_has_a_distinct_command(self):
        self.assertEqual(set(ACTUATOR_COMMANDS), set(Zone))
        self.assertEqual(len(set(ACTUATOR_COMMANDS.values())), len(Zone))


if __name__ == "__main__":
    unittest.main()
