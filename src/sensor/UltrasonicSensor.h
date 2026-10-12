// Reading of the HC-SR04 ultrasonic sensor without stopping the program.

#ifndef ULTRASONIC_SENSOR_H
#define ULTRASONIC_SENSOR_H

#include <Arduino.h>

// Measures distances with the HC-SR04.
// The sensor answers each TRIG pulse with an ECHO pulse that lasts as long as
// the sound takes to reach the object and come back. An interrupt saves the
// time of the start and the end of that pulse, so the program never waits for
// the echo. A measurement is: startMeasurement(), then update() on every loop()
// until it returns true, and then distanceCm().
class UltrasonicSensor {
 public:
  UltrasonicSensor(uint8_t trigPin, uint8_t echoPin);

  // Configures the pins and enables the interrupt of ECHO.
  void begin();

  // Starts a measurement by raising TRIG.
  void startMeasurement();

  // Moves the measurement forward without waiting. Returns true once, when the
  // measurement has finished.
  bool update();

  // Distance of the last measurement in cm, or NAN if no echo arrived in time.
  float distanceCm() const;

 private:
  // Steps of one measurement.
  enum class State : uint8_t {
    Idle,     // No measurement in progress.
    Trigger,  // TRIG is high during TRIGGER_PULSE_US.
    WaitEcho  // Waiting for the end of the echo or for the timeout.
  };

  // Runs on every edge of ECHO and saves its time. It is stored in the internal
  // RAM of the ESP32 (IRAM_ATTR) so the interrupt runs fast.
  static void onEchoChange(void *sensor);

  // Pins of the sensor; they do not change after the constructor.
  const uint8_t trigPin_;
  const uint8_t echoPin_;

  // Progress and result of the measurement; the interrupt does not use them.
  State state_ = State::Idle;
  unsigned long triggerUs_ = 0;  // When TRIG was raised.
  float distanceCm_ = NAN;       // NAN until the first measurement ends.

  // These variables are written by the interrupt. volatile forces the program to
  // read them from memory every time, so it always sees their latest value.
  volatile unsigned long echoStartUs_ = 0;  // Time of the rising edge of ECHO.
  volatile unsigned long echoEndUs_ = 0;    // Time of the falling edge of ECHO.
  volatile bool echoStarted_ = false;       // The echo of this measurement has started.
  volatile bool echoFinished_ = false;      // The echo of this measurement has ended.
};

#endif
