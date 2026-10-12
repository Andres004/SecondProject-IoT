// Constants of the sensor program: pins, timing and speed of sound.
// Board: ESP32 DevKit with 30 pins.

#ifndef SENSOR_CONFIG_H
#define SENSOR_CONFIG_H

#include <Arduino.h>

namespace SensorConfig {

// GPIO27, output to the TRIG pin of the HC-SR04.
constexpr uint8_t PIN_TRIG = 27;

// GPIO26, input from the ECHO pin of the HC-SR04. ECHO gives 5 V, so it passes
// through a 1k/2k voltage divider that lowers it to 3.3 V.
constexpr uint8_t PIN_ECHO = 26;

// Speed of the serial monitor, in bits per second.
constexpr unsigned long SERIAL_BAUD = 115200;

// Time between the start of two measurements: 10 readings per second.
constexpr unsigned long SAMPLE_PERIOD_MS = 100;

// Duration of the TRIG pulse that starts a measurement, as the datasheet requires.
constexpr unsigned long TRIGGER_PULSE_US = 10;

// Maximum wait for the echo. The echo of an object at 400 cm lasts 23.3 ms; if
// no echo ends within this time, the reading is invalid.
constexpr unsigned long ECHO_TIMEOUT_US = 25000;

// Speed of sound in air at 20 degrees Celsius.
constexpr float SOUND_SPEED_CM_PER_US = 0.0343f;

// Centimeters per microsecond of echo. It is half the speed of sound because
// the sound travels to the object and back.
constexpr float CM_PER_ECHO_US = SOUND_SPEED_CM_PER_US / 2;

}  // namespace SensorConfig

#endif
