// Connection, reconnection, sending and receiving of the TCP link.

#include "TcpLink.h"

#include <EventLog.h>

#include <cstdio>

TcpLink::TcpLink(const char *role) : role_(role) {}

void TcpLink::begin(const char *ssid, const char *password, const char *host, uint16_t port) {
  // The network data is kept to retry the connections later.
  ssid_ = ssid;
  host_ = host;
  port_ = port;

  // Station mode: the ESP32 joins an existing WiFi network as a client.
  WiFi.mode(WIFI_STA);
  // Without power saving the radio is always on, so messages arrive at once.
  WiFi.setSleep(false);
  // begin() only starts the connection; update() checks when it is ready.
  WiFi.begin(ssid, password);
  lastWifiRetryMs_ = millis();
  EventLog::write("WIFI_CONNECTING", "ssid=%s", ssid);
}

bool TcpLink::update() {
  const unsigned long now = millis();
  const bool wifiConnected = WiFi.status() == WL_CONNECTED;

  // While the WiFi is up the retry timer keeps restarting. If the WiFi has been
  // down for WIFI_RETRY_INTERVAL_MS, the connection to the network is requested again.
  if (wifiConnected) {
    lastWifiRetryMs_ = now;
  } else if (now - lastWifiRetryMs_ >= WIFI_RETRY_INTERVAL_MS) {
    lastWifiRetryMs_ = now;
    WiFi.reconnect();
    EventLog::write("WIFI_RETRY", "ssid=%s", ssid_);
  }

  // The connection is lost when the WiFi drops or when the server closes it.
  // stop() releases the socket so a new connection can be opened later.
  if (connected_ && !(wifiConnected && client_.connected())) {
    connected_ = false;
    client_.stop();
    EventLog::write("SERVER_LOST", "wifi=%s", wifiConnected ? "up" : "down");
  }

  // With a connection, the only task is to read what the server sent.
  if (connected_) {
    return readLine();
  }

  // Without a connection, try to connect again every RECONNECT_INTERVAL_MS.
  // The time is measured with millis(), so the program keeps running meanwhile.
  if (wifiConnected && now - lastConnectMs_ >= RECONNECT_INTERVAL_MS) {
    lastConnectMs_ = now;
    connect();
  }
  return false;
}

bool TcpLink::send(const char *message) {
  // The message is written only if there is a connection; printf() returns the
  // number of bytes written, so 0 means that the write failed.
  const bool sent = connected_ && client_.printf("%s\n", message) > 0;

  // TX is a message that left; TX_FAILED is a message that could not be sent.
  EventLog::write(sent ? "TX" : "TX_FAILED", "%s", message);
  return sent;
}

bool TcpLink::isConnected() const { return connected_; }

const char *TcpLink::line() const { return line_; }

void TcpLink::connect() {
  // connect() waits at most CONNECT_TIMEOUT_MS for the answer of the server.
  if (!client_.connect(host_, port_, CONNECT_TIMEOUT_MS)) {
    EventLog::write("SERVER_UNREACHABLE", "server=%s:%u", host_, port_);
    return;
  }

  // Turn off the Nagle algorithm, which holds short messages back to group them.
  client_.setNoDelay(true);
  connected_ = true;

  // A new connection starts with an empty line buffer.
  lineLength_ = 0;
  lineTooLong_ = false;
  EventLog::write("SERVER_CONNECTED", "server=%s:%u local_ip=%s", host_, port_,
                  WiFi.localIP().toString().c_str());

  // REGISTER tells the server whether this client is the sensor or the actuator.
  char message[MAX_LINE_LENGTH + 1];
  snprintf(message, sizeof(message), "REGISTER %s", role_);
  send(message);
}

bool TcpLink::readLine() {
  // TCP delivers a stream of bytes; each '\n' marks the end of one message.
  // available() tells how many bytes have arrived, so read() never waits.
  while (client_.available() > 0) {
    const char c = static_cast<char>(client_.read());
    if (c == '\n') {
      // End of the message: close the text and leave the buffer ready for the
      // next line. A line that was too long is logged but not returned.
      const bool complete = !lineTooLong_;
      line_[lineLength_] = '\0';
      lineLength_ = 0;
      lineTooLong_ = false;
      EventLog::write(complete ? "RX" : "RX_TOO_LONG", "%s", line_);
      if (complete) {
        return true;
      }
    } else if (lineLength_ < MAX_LINE_LENGTH) {
      // Normal character: add it to the line being built.
      line_[lineLength_++] = c;
    } else {
      // No room left: the rest of the line is ignored and the line is discarded.
      lineTooLong_ = true;
    }
  }
  return false;
}