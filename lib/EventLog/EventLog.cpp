// Builds each line of the event log and prints it on the serial monitor.

#include "EventLog.h"

#include <Arduino.h>

#include <cstdarg>
#include <cstdio>

namespace {

// Maximum length of the details of one event; longer details are cut.
constexpr size_t MAX_DETAILS_LENGTH = 96;

}  // namespace

namespace EventLog {

void write(const char *event, const char *format, ...) {
  // Buffer for the details text, with one extra place for the end of the text.
  char details[MAX_DETAILS_LENGTH + 1];

  // The "..." values are read with va_list and placed into the format by|
  // vsnprintf(), which never writes beyond the size of the buffer.
  va_list args;
  va_start(args, format);
  vsnprintf(details, sizeof(details), format, args);
  va_end(args);

  // millis() gives the time since the board started. Fixed widths keep the
  // time and the event name aligned in columns.
  Serial.printf("[t_ms=%9lu] %-18s %s\n", millis(), event, details);
}

}  // namespace EventLog