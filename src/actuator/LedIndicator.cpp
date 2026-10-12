// Writing of the LED states and timing of the blinking.

#include "LedIndicator.h"

#include "ActuatorConfig.h"

// The pins are stored in the order of Led: red, yellow, white.
LedIndicator::LedIndicator(uint8_t redPin, uint8_t yellowPin, uint8_t whitePin)
    : pins_{redPin, yellowPin, whitePin} {}

void LedIndicator::begin() {
  // Every LED pin is an output.
  for (const uint8_t pin : pins_) {
    pinMode(pin, OUTPUT);
  }

  // Show the starting state (all LEDs blinking) and start its timer.
  lastToggleMs_ = millis();
  writePins();
}

void LedIndicator::show(Led led, LedMode mode) {
  // The same state again: keep the blinking as it is.
  if (led == led_ && mode == mode_) {
    return;
  }

  // A different state is shown at once, starting with the LED lit, and the
  // blinking timer starts again from this moment.
  led_ = led;
  mode_ = mode;
  lit_ = true;
  lastToggleMs_ = millis();
  writePins();
}

void LedIndicator::update() {
  // In Blink mode the lit phase is inverted every BLINK_INTERVAL_MS.
  // The time is measured with millis(), so the program never waits here.
  const unsigned long now = millis();
  if (mode_ == LedMode::Blink && now - lastToggleMs_ >= ActuatorConfig::BLINK_INTERVAL_MS) {
    lastToggleMs_ = now;
    lit_ = !lit_;
    writePins();
  }
}

void LedIndicator::writePins() {
  // A pin is high only if its LED is chosen and the blinking is in its lit phase.
  // In On mode lit_ is always true, so the chosen LED stays on.
  for (size_t i = 0; i < LED_COUNT; i++) {
    const bool selected = led_ == Led::All || static_cast<size_t>(led_) == i;
    digitalWrite(pins_[i], selected && lit_ ? HIGH : LOW);
  }
}
