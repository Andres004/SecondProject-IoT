# Evidencia B07: Estabilidad y frecuencia de muestreo

Prueba B07 de la sección 4.3 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| server_20261013_153535.csv | CSV del servidor: 12 min de funcionamiento continuo, con el blanco movido cada 2 min entre 30, 10 y 60 cm |
| B07_OI1.log | Log del monitor serie de OI-1 durante toda la corrida |
| B07_OI2.log | Log del monitor serie de OI-2 durante toda la corrida |
| B07_analisis.txt | Salida de `analyze_log.py` para el CSV y los dos logs |

| Medida | Valor | Criterio | Veredicto |
|---|---|---|---|
| Duración con lecturas | 12.0 min | ≥ 10 min | PASS |
| Lecturas recibidas / perdidas / inválidas | 7202 / 0 / 0 | — | — |
| Lecturas por ventana de 10 s | 97 a 102 (media 100.0) | ≥ 50 | PASS (RNF4) |
| Intervalo entre lecturas | media 100.0 ms, p95 118.8 ms, máx. 926.9 ms | máx. < 1000 ms | PASS (RNF1) |
| Reinicios de `seq` y desconexiones | 0 y 0 | 0 | PASS (RNF1) |
| Reinicios de OI-1 y OI-2 | 0 y 0 | 0 | PASS (RNF1) |
| Zonas y comandos | 8 cambios, todos con su `SET` | sin diferencias | PASS (RF2/RF5/RF6) |
| Protocolo | 0 errores, un `ACK` por `SET` | sin errores | PASS (RF4) |

La línea `RNF3` de `B07_analisis.txt` sale `FAIL` porque el `ACK` del cambio a FAR del minuto 4 (seq 2859) tardó 1295.9 ms por un retraso de la red WiFi. B07 no mide RNF3; el caso se analiza en §4.4 del informe. Los `SERVER_UNREACHABLE` y `TX_FAILED` del inicio de cada log son de antes de iniciar el servidor, y el `SERVER_LOST` final, de detenerlo.