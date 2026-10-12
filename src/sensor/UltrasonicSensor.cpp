// Steps of each measurement and interrupt of the ECHO pin.

#include "UltrasonicSensor.h"

#include "SensorConfig.h"

UltrasonicSensor::UltrasonicSensor(uint8_t trigPin, uint8_t echoPin)
    : trigPin_(trigPin), echoPin_(echoPin) {}

void UltrasonicSensor::begin() {
  // TRIG is an output that rests low; ECHO is an input driven by the sensor.
  pinMode(trigPin_, OUTPUT);
  digitalWrite(trigPin_, LOW);
  pinMode(echoPin_, INPUT);

  // CHANGE: onEchoChange() runs on the rising and on the falling edge of ECHO.
  // "this" is passed to the interrupt so it can save the times in this object.
  attachInterruptArg(echoPin_, onEchoChange, this, CHANGE);
}

void UltrasonicSensor::startMeasurement() {
  // Clear the echo flags, so only the echo of this measurement counts.
  echoStarted_ = false;
  echoFinished_ = false;

  // Raise TRIG and save the moment; update() lowers it after TRIGGER_PULSE_US.
  state_ = State::Trigger;
  triggerUs_ = micros();
  digitalWrite(trigPin_, HIGH);
}

bool UltrasonicSensor::update() {
  // Time since TRIG was raised; it is used for the pulse and for the timeout.
  const unsigned long elapsedUs = micros() - triggerUs_;

  // The TRIG pulse ends once it has lasted TRIGGER_PULSE_US. Then the sensor
  // sends the ultrasound and the program waits for the echo.
  if (state_ == State::Trigger && elapsedUs >= SensorConfig::TRIGGER_PULSE_US) {
    digitalWrite(trigPin_, LOW);
    state_ = State::WaitEcho;
  }

  // Nothing else to do while idle or while TRIG is still high.
  if (state_ != State::WaitEcho) {
    return false;
  }

  // The measurement ends when the echo ends, or as invalid when the time runs out.
  // The distance is the duration of the echo multiplied by CM_PER_ECHO_US.
  if (echoFinished_) {
    distanceCm_ = static_cast<float>(echoEndUs_ - echoStartUs_) * SensorConfig::CM_PER_ECHO_US;
  } else if (elapsedUs >= SensorConfig::ECHO_TIMEOUT_US) {
    distanceCm_ = NAN;
  } else {
    // The echo has not ended yet: keep waiting on the next loop().
    return false;
  }

  // The result is ready and the sensor can start another measurement.
  state_ = State::Idle;
  return true;
}

float UltrasonicSensor::distanceCm() const { return distanceCm_; }

void IRAM_ATTR UltrasonicSensor::onEchoChange(void *sensor) {
  // The interrupt receives the object that attached it and saves the time of
  // this edge. It does little work, so it ends quickly.
  auto *self = static_cast<UltrasonicSensor *>(sensor);
  const unsigned long nowUs = micros();

  // A high level means the edge was rising (start of the echo); a low level
  // means it was falling (end of the echo). A falling edge only counts if the
  // rising edge of the same echo was seen.
  if (digitalRead(self->echoPin_) == HIGH) {
    self->echoStartUs_ = nowUs;
    self->echoStarted_ = true;
  } else if (self->echoStarted_) {
    self->echoEndUs_ = nowUs;
    self->echoFinished_ = true;
  }
}