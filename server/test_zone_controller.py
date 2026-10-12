"""Unit tests of the control algorithm in zone_controller.py."""

import math
import unittest

from zone_controller import ACTUATOR_COMMANDS, Zone, ZoneController, classify


def controller_in(first_reading: float) -> ZoneController:
    """Return a controller already placed in the zone of first_reading."""
    controller = ZoneController()
    controller.update(first_reading)
    return controller


class ClassifyTest(unittest.TestCase):
    """Exact boundaries of the ranges in classify()."""

    def test_blind_zone_boundary(self):
        """1.9 cm is invalid and 2.0 cm is the first NEAR value."""
        self.assertEqual(classify(1.9), Zone.ERROR)
        self.assertEqual(classify(2.0), Zone.NEAR)

    def test_near_medium_boundary(self):
        """19.9 cm is NEAR and 20.0 cm is MEDIUM."""
        self.assertEqual(classify(19.9), Zone.NEAR)
        self.assertEqual(classify(20.0), Zone.MEDIUM)

    def test_medium_far_boundary(self):
        """39.9 cm is MEDIUM and 40.0 cm is FAR."""
        self.assertEqual(classify(39.9), Zone.MEDIUM)
        self.assertEqual(classify(40.0), Zone.FAR)

    def test_max_range_boundary(self):
        """400.0 cm is FAR and 400.1 cm is invalid."""
        self.assertEqual(classify(400.0), Zone.FAR)
        self.assertEqual(classify(400.1), Zone.ERROR)

    def test_non_numeric_readings(self):
        """NaN and infinity are invalid readings."""
        self.assertEqual(classify(math.nan), Zone.ERROR)
        self.assertEqual(classify(math.inf), Zone.ERROR)


class HysteresisTest(unittest.TestCase):
    """The zone changes only after a boundary is passed by HYSTERESIS_CM."""

    def assert_transition(self, start, stay, change, expected):
        """From the zone of start, stay keeps the zone and change moves it."""
        controller = controller_in(start)
        initial_zone = controller.zone
        self.assertFalse(controller.update(stay))
        self.assertEqual(controller.zone, initial_zone)
        self.assertTrue(controller.update(change))
        self.assertEqual(controller.zone, expected)

    def test_near_to_medium(self):
        """NEAR stays at 21.9 cm and changes to MEDIUM at 22.0 cm."""
        self.assert_transition(10.0, 21.9, 22.0, Zone.MEDIUM)

    def test_medium_to_near(self):
        """MEDIUM stays at 18.0 cm and changes to NEAR at 17.9 cm."""
        self.assert_transition(30.0, 18.0, 17.9, Zone.NEAR)

    def test_medium_to_far(self):
        """MEDIUM stays at 41.9 cm and changes to FAR at 42.0 cm."""
        self.assert_transition(30.0, 41.9, 42.0, Zone.FAR)

    def test_far_to_medium(self):
        """FAR stays at 38.0 cm and changes to MEDIUM at 37.9 cm."""
        self.assert_transition(50.0, 38.0, 37.9, Zone.MEDIUM)

    def test_jump_near_to_far(self):
        """From NEAR, a reading of 42.0 cm goes straight to FAR."""
        self.assert_transition(10.0, 21.9, 42.0, Zone.FAR)

    def test_jump_far_to_near(self):
        """From FAR, a reading of 17.9 cm goes straight to NEAR."""
        self.assert_transition(50.0, 38.0, 17.9, Zone.NEAR)

    def test_first_reading_is_classified_directly(self):
        """The first reading leaves ERROR without hysteresis."""
        controller = ZoneController()
        self.assertEqual(controller.zone, Zone.ERROR)
        self.assertTrue(controller.update(20.0))
        self.assertEqual(controller.zone, Zone.MEDIUM)


class InvalidReadingTest(unittest.TestCase):
    """Isolated invalid readings are tolerated; a run of them gives ERROR."""

    def test_two_invalid_readings_keep_zone_and_hysteresis(self):
        """Two invalid readings keep MEDIUM and its hysteresis thresholds."""
        controller = controller_in(30.0)
        self.assertFalse(controller.update(math.nan))
        self.assertFalse(controller.update(math.nan))
        self.assertEqual(controller.zone, Zone.MEDIUM)
        self.assertFalse(controller.update(18.0))
        self.assertEqual(controller.zone, Zone.MEDIUM)

    def test_third_invalid_reading_enters_error(self):
        """The third invalid reading in a row changes to ERROR."""
        controller = controller_in(30.0)
        controller.update(math.nan)
        controller.update(math.nan)
        self.assertTrue(controller.update(math.nan))
        self.assertEqual(controller.zone, Zone.ERROR)

    def test_valid_reading_restarts_the_invalid_count(self):
        """A valid reading between invalid ones restarts the count."""
        controller = controller_in(30.0)
        for reading in (math.nan, math.nan, 30.0, math.nan, math.nan):
            controller.update(reading)
        self.assertEqual(controller.zone, Zone.MEDIUM)

    def test_reset_enters_error(self):
        """reset() changes to ERROR and reports the change only once."""
        controller = controller_in(30.0)
        self.assertTrue(controller.reset())
        self.assertEqual(controller.zone, Zone.ERROR)
        self.assertFalse(controller.reset())


class CommandTest(unittest.TestCase):
    """Commands that the actuator receives for each zone."""

    def test_every_zone_has_a_distinct_command(self):
        """Every zone has a command and no two zones share one."""
        self.assertEqual(set(ACTUATOR_COMMANDS), set(Zone))
        self.assertEqual(len(set(ACTUATOR_COMMANDS.values())), len(Zone))


if __name__ == "__main__":
    unittest.main()
