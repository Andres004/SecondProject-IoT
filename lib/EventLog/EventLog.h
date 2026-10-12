// Event log of the ESP32 programs. Each event is printed on the serial monitor
// as one line that starts with t_ms, the time in milliseconds since the board
// started, so the moment of every event can be measured.

#ifndef EVENT_LOG_H
#define EVENT_LOG_H

namespace EventLog {

// Prints one line with the current t_ms, the event name and its details.
// The details are written with a printf format followed by its values.
void write(const char *event, const char *format, ...);

}  // namespace EventLog

#endif
