// Control of the red, yellow and white LEDs, with blinking that does not stop
// the program.

#ifndef LED_INDICATOR_H
#define LED_INDICATOR_H

#include <Arduino.h>

// LED chosen by a command; All chooses the three LEDs. The values of Red,
// Yellow and White are also the positions of their pins inside LedIndicator.
enum class Led : uint8_t { Red, Yellow, White, All };

// Behaviour of the chosen LED.
enum class LedMode : uint8_t { On, Blink };

// Shows one state on the three LEDs: the chosen LED is on or blinking and the
// others are off. Blinking is timed with millis(), so update() must run on
// every loop(). At the start all LEDs blink.
class LedIndicator {
 public:
  LedIndicator(uint8_t redPin, uint8_t yellowPin, uint8_t whitePin);

  // Configures the pins as outputs and shows the starting state.
  void begin();

  // Shows a state at once, beginning with the LED lit. If it is the state already
  // shown, nothing changes, so the blinking keeps its rhythm.
  void show(Led led, LedMode mode);

  // Switches the blinking LED on or off every BLINK_INTERVAL_MS.
  void update();

 private:
  // Writes the current state on the three pins.
  void writePins();

  static constexpr size_t LED_COUNT = 3;
  const uint8_t pins_[LED_COUNT];  // In the order of Led: red, yellow, white.

  // State shown now. It starts as all LEDs blinking.
  Led led_ = Led::All;
  LedMode mode_ = LedMode::Blink;
  bool lit_ = true;                 // Phase of the blinking: lit or off.
  unsigned long lastToggleMs_ = 0;  // When lit_ changed for the last time.
};

#endif
