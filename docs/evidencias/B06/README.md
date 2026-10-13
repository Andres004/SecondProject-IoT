# Evidencia B06: Reinicio del servidor con el sistema completo

Prueba B06 de la sección 4.3 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| server_20261013_152623.csv | Arranque inicial del servidor, antes del primer reinicio |
| server_20261013_152707.csv | Reinicio 1 |
| server_20261013_152724.csv | Reinicio 2 |
| B06_OI1.log | Log del monitor serie de OI-1 durante toda la prueba |
| B06_OI2.log | Log del monitor serie de OI-2 durante toda la prueba |
| B06_analisis.txt | Salida de `analyze_log.py` para los tres CSV y los dos logs |
| B06.mp4 | LEDs durante los reinicios: los tres parpadean con el servidor detenido y vuelve el amarillo al reiniciarlo |

| Reinicio | Servidor detenido | `REGISTER SENSOR` tras `START` | `REGISTER ACTUATOR` tras `START` | Estado recuperado |
|---|---|---|---|---|
| 1 | ~9 s | 1647 ms | 1654 ms | ERROR → MEDIUM (seq 317, 21.9 cm), `ACK` en 58.9 ms |
| 2 | ~7 s | 897 ms | 922 ms | MEDIUM; OI-2 recibe `SET 0 YELLOW BLINK` al registrarse, `ACK` en 39.7 ms |

Reintentos de conexión mientras el servidor estuvo detenido: OI-1 cada 1777–2000 ms y OI-2 cada 1773–2000 ms. Ninguna placa se reinició durante la prueba.

El CSV del arranque inicial (152623) no mide ningún reinicio. Los monitores serie se abrieron con el servidor ya en marcha, y abrir un monitor reinicia la placa. Por eso ese CSV muestra los cambios de zona mientras se acomodaba el blanco, 4 `SET` sin `ACK` enviados a la conexión vieja de OI-2 mientras la placa reiniciaba (`DISCONNECT ACTUATOR/error`), y la pérdida de OI-1 por silencio (`SENSOR/timeout`) mientras OI-1 reiniciaba. Las líneas `FAIL` de RNF1 y RF4 en `B06_analisis.txt` para ese CSV corresponden a esos reinicios por el monitor, no a los reinicios del servidor.