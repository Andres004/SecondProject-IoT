// Program of the actuator ESP32: receives "SET <seq> <led> <mode>" commands
// from the server, shows them on the LEDs and confirms each one with
// "ACK <seq>". Without a connection to the server all LEDs blink (ERROR state).

#include <Arduino.h>
#include <EventLog.h>
#include <TcpLink.h>

#include <cstdio>
#include <cstring>

#include "ActuatorConfig.h"
#include "LedIndicator.h"
#include "Secrets.h"

namespace {

// Size of the texts that hold a LED or mode name: up to 7 characters plus the
// end of the text. The "%7s" fields of sscanf() read 7 characters at most.
constexpr size_t NAME_SIZE = 8;

// Objects used only in this file.
TcpLink serverLink("ACTUATOR");
LedIndicator leds(ActuatorConfig::PIN_LED_RED, ActuatorConfig::PIN_LED_YELLOW,
                  ActuatorConfig::PIN_LED_WHITE);

// Reads a "SET <seq> <led> <mode>" line. Returns false if the line is not a
// valid SET command.
bool parseSet(const char *line, unsigned long &seq, Led &led, LedMode &mode) {
  // sscanf() returns how many fields it filled: a number and two names are needed.
  char ledName[NAME_SIZE];
  char modeName[NAME_SIZE];
  if (sscanf(line, "SET %lu %7s %7s", &seq, ledName, modeName) != 3) {
    return false;
  }

  // Name of the LED in the protocol -> value of Led.
  if (strcmp(ledName, "RED") == 0) {
    led = Led::Red;
  } else if (strcmp(ledName, "YELLOW") == 0) {
    led = Led::Yellow;
  } else if (strcmp(ledName, "WHITE") == 0) {
    led = Led::White;
  } else if (strcmp(ledName, "ALL") == 0) {
    led = Led::All;
  } else {
    return false;
  }

  // Name of the mode in the protocol -> value of LedMode.
  if (strcmp(modeName, "ON") == 0) {
    mode = LedMode::On;
  } else if (strcmp(modeName, "BLINK") == 0) {
    mode = LedMode::Blink;
  } else {
    return false;
  }
  return true;
}

// Shows a SET command on the LEDs and confirms it with "ACK <seq>". The other
// lines from the server (OK, ERROR) need no action.
void handleLine(const char *line) {
  unsigned long seq = 0;
  Led led = Led::All;
  LedMode mode = LedMode::Blink;
  if (!parseSet(line, seq, led, mode)) {
    return;
  }
  leds.show(led, mode);

  // The ACK is sent once the LEDs already show the command. It carries the same
  // seq, so the server knows which command was applied.
  char ack[TcpLink::MAX_LINE_LENGTH + 1];
  snprintf(ack, sizeof(ack), "ACK %lu", seq);
  serverLink.send(ack);
}

}  // namespace

// Runs once at power on: starts the serial monitor, the LEDs and the WiFi.
void setup() {
  Serial.begin(ActuatorConfig::SERIAL_BAUD);

  // The first line of the log shows the pins of the three LEDs.
  EventLog::write("BOOT", "ACTUATOR red=%d yellow=%d white=%d", ActuatorConfig::PIN_LED_RED,
                  ActuatorConfig::PIN_LED_YELLOW, ActuatorConfig::PIN_LED_WHITE);

  // The LEDs start blinking at once, before there is any connection.
  leds.begin();

  // The WiFi starts connecting in the background; loop() runs from now on.
  serverLink.begin(Secrets::WIFI_SSID, Secrets::WIFI_PASSWORD, Secrets::SERVER_HOST,
                   Secrets::SERVER_PORT);
}

// Runs again and again: applies the commands of the server and keeps the LEDs blinking.
// No step waits, so the blinking keeps its rhythm while messages arrive.
void loop() {
  // Each complete line received from the server is handled right away.
  if (serverLink.update()) {
    handleLine(serverLink.line());
  }

  // Without a connection to the server, the LEDs show the ERROR state.
  if (!serverLink.isConnected()) {
    leds.show(Led::All, LedMode::Blink);
  }

  // Advances the blinking of the LED that is shown.
  leds.update();
}