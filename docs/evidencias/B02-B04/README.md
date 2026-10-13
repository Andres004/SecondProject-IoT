# Evidencia B02, B03 y B04: Pruebas de sistema del servidor

Pruebas B02, B03 y B04 de la sección 4.3 del informe, ejecutadas juntas con `python -m tests.system_check` desde `server/`, con el servidor en marcha y las dos placas apagadas. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| B02-B04_salida.txt | Salida de `system_check.py`: los 14 casos y el resumen final |
| server_*.csv | CSV que escribió el servidor durante la ejecución; varios casos lo leen para comprobar sus eventos |

| Prueba | Clase | Casos | Resultado |
|---|---|---|---|
| B02 | `ProtocolTest` | 4 | 4 `ok` |
| B03 | `ControlTest` | 3 | 3 `ok` |
| B04 | `DisconnectionTest` | 7 | 7 `ok` |

Resumen final: `Ran 14 tests in 2.889s` y `OK`.

Tiempos que informa la salida, desde la última lectura del sensor hasta que `SET 0 ALL BLINK` llega al actuador simulado: 2 ms cuando el sensor cierra la conexión (`test_sensor_closes`) y 1016 ms cuando el sensor queda en silencio (`test_silent_sensor`; RF7 (a) pide entre 1.0 y 1.5 s).