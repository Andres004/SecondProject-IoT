// Program of the sensor ESP32: measures the distance 10 times per second and
// sends each reading to the server as "POST <seq> <cm>".

#include <Arduino.h>
#include <EventLog.h>
#include <TcpLink.h>

#include <cmath>
#include <cstdio>

#include "Secrets.h"
#include "SensorConfig.h"
#include "UltrasonicSensor.h"

namespace {

// Objects and variables used only in this file.
TcpLink serverLink("SENSOR");
UltrasonicSensor sensor(SensorConfig::PIN_TRIG, SensorConfig::PIN_ECHO);
unsigned long lastSampleMs = 0;  // When the last measurement started.
unsigned long seq = 0;           // Number of the last reading; it grows by one per reading.

// Sends one reading to the server; an invalid reading is sent as NAN.
void sendReading(float distanceCm) {
  // Each reading gets the next sequence number, even if it cannot be sent.
  char message[TcpLink::MAX_LINE_LENGTH + 1];
  seq++;

  // A valid distance is sent in cm with one decimal place.
  if (std::isnan(distanceCm)) {
    snprintf(message, sizeof(message), "POST %lu NAN", seq);
  } else {
    snprintf(message, sizeof(message), "POST %lu %.1f", seq, distanceCm);
  }
  serverLink.send(message);
}

}  // namespace

// Runs once at power on: starts the serial monitor, the sensor and the WiFi.
void setup() {
  Serial.begin(SensorConfig::SERIAL_BAUD);

  // The first line of the log shows the pins and the sampling period in use.
  EventLog::write("BOOT", "SENSOR trig=%d echo=%d period_ms=%lu", SensorConfig::PIN_TRIG,
                  SensorConfig::PIN_ECHO, SensorConfig::SAMPLE_PERIOD_MS);
  sensor.begin();

  // The WiFi starts connecting in the background; loop() runs from now on.
  serverLink.begin(Secrets::WIFI_SSID, Secrets::WIFI_PASSWORD, Secrets::SERVER_HOST,
                   Secrets::SERVER_PORT);
}

// Runs again and again: keeps the connection, starts measurements and sends readings.
// No step waits, so each pass of loop() takes very little time.
void loop() {
  // Keeps the WiFi and the server connection alive, and reconnects if needed.
  serverLink.update();

  // A new measurement starts every SAMPLE_PERIOD_MS, timed with millis().
  const unsigned long now = millis();
  if (now - lastSampleMs >= SensorConfig::SAMPLE_PERIOD_MS) {
    lastSampleMs = now;
    sensor.startMeasurement();
  }

  // Each reading is sent as soon as its measurement finishes.
  if (sensor.update()) {
    sendReading(sensor.distanceCm());
  }
}
