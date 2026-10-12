// Network settings of both ESP32: WiFi network and address of the server.
// This file is a template. A copy named Secrets.h holds the real values and
// is never uploaded to the repository.

#ifndef SECRETS_H
#define SECRETS_H

#include <Arduino.h>

namespace Secrets {

// Name and password of the WiFi network. The ESP32 only connects to 2.4 GHz networks.
constexpr char WIFI_SSID[] = "YOUR_NETWORK_NAME";
constexpr char WIFI_PASSWORD[] = "YOUR_NETWORK_PASSWORD";

// IP address of the PC that runs the server, and the TCP port where it listens.
constexpr char SERVER_HOST[] = "192.168.0.100";
constexpr uint16_t SERVER_PORT = 5050;

}  // namespace Secrets

#endif
