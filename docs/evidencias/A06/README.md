# Evidencia A06: Lecturas inválidas con el hardware

Prueba A06 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| A06_OI1.log | Log del monitor serie de OI-1 durante la prueba |
| A06_salida.txt | Salida de `analyze_log.py` para el CSV y el log de OI-1 |
| A06.mp4 | LEDs durante la prueba: amarillo parpadeando (MEDIUM) y los tres parpadeando (ERROR) mientras ECHO está desconectado |

Desconexiones de ECHO (seq del CSV; tiempos de la tercera `NAN` según el reloj de OI-1):

| Desconexión | Primera `NAN` | MEDIUM → ERROR | Tercera `NAN` tras la primera | ERROR → MEDIUM |
|---|---|---|---|---|
| 1 | 221 | 223 | 199 ms | 270 (26.1 cm) |
| 2 | 320 | 322 | 200 ms | 343 (26.1 cm) |
| 3 | 375 | 377 | 199 ms | 453 (27.0 cm), después del corte de red |

Durante la tercera desconexión hubo un corte de la red WiFi de unos 6 s: el `ACK` de OI-2 al `SET` 377 tardó 5674.4 ms y el servidor perdió a OI-1 (`SENSOR/timeout` 1015 ms después de la última lectura). OI-1 registró `SERVER_LOST wifi=up` y se reconectó solo 4.2 s después, sin reiniciarse (`seq` continuo de 173 a 453). Las lecturas 396 a 440 se perdieron en ese corte; el log de OI-1 muestra que en ese tiempo ECHO se reconectó (seq 405–425) y se desconectó otra vez (seq 426–440). Las líneas `FAIL` de RNF1, RNF3 y RNF4 en `A06_salida.txt` corresponden a este corte. Se analiza en §4.4 del informe.