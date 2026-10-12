// TCP connection between an ESP32 and the control server, over WiFi.

#ifndef TCP_LINK_H
#define TCP_LINK_H

#include <Arduino.h>
#include <WiFi.h>

// Keeps one ESP32 connected to the server and exchanges lines of text with it.
// update() must run on every loop(). It never stops the program: while the
// WiFi or the server is missing, it only retries every few seconds.
// After each connection it sends "REGISTER <role>" so the server knows which
// client it is. Every message sent and received is printed in the event log.
class TcpLink {
 public:
  // Time between two attempts to connect to the server.
  static constexpr unsigned long RECONNECT_INTERVAL_MS = 2000;
  // Maximum duration of one connection attempt. An attempt only lasts this long
  // when the server does not answer.
  static constexpr int32_t CONNECT_TIMEOUT_MS = 250;
  // Time without WiFi after which the WiFi connection is requested again.
  static constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10000;
  // Maximum length of a message; longer lines from the server are discarded.
  static constexpr size_t MAX_LINE_LENGTH = 32;

  // role is the name sent with REGISTER: "SENSOR" or "ACTUATOR".
  explicit TcpLink(const char *role);

  // Starts the WiFi connection without waiting for it and saves the address of
  // the server. WiFi power saving is turned off so messages are not delayed.
  void begin(const char *ssid, const char *password, const char *host, uint16_t port);

  // Keeps the WiFi and the server connection alive and reads what the server
  // sent. Returns true when a complete line has arrived; line() returns it.
  bool update();

  // Sends one message to the server and adds the '\n' that ends it.
  // Returns false if the message could not be sent.
  bool send(const char *message);

  // true while there is a connection with the server.
  bool isConnected() const;

  // Last line received from the server, without the '\n'.
  const char *line() const;

 private:
  // Opens the connection with the server and sends REGISTER.
  void connect();

  // Reads the bytes that have already arrived, without waiting for more.
  // Returns true when they complete a line.
  bool readLine();

  // Data saved by the constructor and by begin().
  const char *role_;
  const char *ssid_ = nullptr;
  const char *host_ = nullptr;
  uint16_t port_ = 0;

  // TCP socket of the Arduino WiFi library and the state of the connection.
  WiFiClient client_;
  bool connected_ = false;

  // Timers of the retries, measured with millis().
  unsigned long lastConnectMs_ = 0;    // When the last connection attempt started.
  unsigned long lastWifiRetryMs_ = 0;  // Last time the WiFi was up or was requested again.

  // Line being received from the server; the extra place holds the end of the text.
  char line_[MAX_LINE_LENGTH + 1] = "";
  size_t lineLength_ = 0;
  bool lineTooLong_ = false;  // The line being received exceeds MAX_LINE_LENGTH.
};

#endif
