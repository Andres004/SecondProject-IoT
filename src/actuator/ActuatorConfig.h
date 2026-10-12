// Constants of the actuator program: LED pins and blinking speed.
// Board: ESP32-DevKitC with 38 pins.

#ifndef ACTUATOR_CONFIG_H
#define ACTUATOR_CONFIG_H

#include <Arduino.h>

namespace ActuatorConfig {

// GPIOs of the LEDs. Each LED is connected through a 220 ohm resistor.
constexpr uint8_t PIN_LED_RED = 25;
constexpr uint8_t PIN_LED_YELLOW = 26;
constexpr uint8_t PIN_LED_WHITE = 27;

// Speed of the serial monitor, in bits per second.
constexpr unsigned long SERIAL_BAUD = 115200;

// Time between two changes of a blinking LED: 250 ms on, 250 ms off.
constexpr unsigned long BLINK_INTERVAL_MS = 250;

}  // namespace ActuatorConfig

#endif
