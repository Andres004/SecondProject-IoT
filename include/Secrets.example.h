// Template of the network settings of both ESP32 programs.
// Copy this file as include/Secrets.h and fill in the values of your network.
// Secrets.h is listed in .gitignore, so the real password is never versioned.

#ifndef SECRETS_H
#define SECRETS_H

#include <Arduino.h>

namespace Secrets {

// WiFi network of 2.4 GHz; the ESP32 cannot join 5 GHz networks.
constexpr char WIFI_SSID[] = "your-network";
constexpr char WIFI_PASSWORD[] = "your-password";

// IP address of the PC that runs server/tcp_server.py. The server prints it
// in its START event when it starts.
constexpr char SERVER_HOST[] = "192.168.1.32";

// TCP port of the server; it must match PORT in server/config.py.
constexpr uint16_t SERVER_PORT = 5050;

}  // namespace Secrets

#endif
