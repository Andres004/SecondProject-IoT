# Evidencia B05: Firmware de OI-1 y OI-2 con un servidor de prueba

Prueba B05 de la sección 4.3 del informe, ejecutada con `python -m tests.client_check` desde `server/`, con `tcp_server.py` detenido y una sola placa encendida a la vez. Fecha: 13/10/2026.

| Archivo | Qué muestra | Caso |
|---|---|---|
| B05A_salida.txt | Salida de `client_check.py ActuatorCheck`: 4 pasos y el tiempo de cada `ACK` | B05-A |
| B05A_OI2.log | Log del monitor serie de OI-2 durante B05-A | B05-A |
| B05A_analisis.txt | Salida de `analyze_log.py` para el log de OI-2 | B05-A |
| B05-A.mp4 | LEDs de OI-2: las 8 combinaciones, el blanco fijo durante las líneas inválidas y los tres parpadeando con el servidor cerrado | B05-A |
| B05B_salida.txt | Salida de `client_check.py SensorCheck`: 4 pasos, frecuencia de lecturas y salto de `seq` | B05-B |
| B05B_OI1.log | Log del monitor serie de OI-1 durante B05-B | B05-B |
| B05B_analisis.txt | Salida de `analyze_log.py` para el log de OI-1 | B05-B |

| Caso | Pasos | Resultado | Medidas |
|---|---|---|---|
| B05-A (OI-2) | 4 | 4 `ok` | `ACK` en 31–203 ms; registro 47 ms después de que el servidor volvió a escuchar; reintentos cada 1770–2000 ms; 1 `RX_TOO_LONG`; 0 reinicios |
| B05-B (OI-1) | 4 | 4 `ok` | 10.2 lecturas/s; registro 109 ms después de que el servidor volvió a escuchar; `seq` de 134 a 190 sin reinicio; reintentos cada 1814–2000 ms; 1 `RX_TOO_LONG`; 0 reinicios |

En cada log, el segundo `SERVER_LOST` corresponde al cierre de la conexión al terminar el script.