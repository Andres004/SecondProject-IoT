/**
 * @file Secrets.example.h
 * @brief Network configuration template. Copy it as Secrets.h and fill in real values.
 *        Secrets.h is listed in .gitignore, so credentials are never committed.
 */
#ifndef SECRETS_H
#define SECRETS_H

#include <Arduino.h>

namespace Secrets {
constexpr char WIFI_SSID[] = "YOUR_NETWORK_NAME";
constexpr char WIFI_PASSWORD[] = "YOUR_NETWORK_PASSWORD";
constexpr char SERVER_HOST[] = "192.168.0.100";  ///< IP address of the PC running the server
constexpr uint16_t SERVER_PORT = 5050;           ///< Must match PORT in server/config.py
}  // namespace Secrets

#endif