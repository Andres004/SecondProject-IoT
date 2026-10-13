# Evidencia A08: Caída de la red WiFi

Prueba A08 de la sección 4.2 del informe. Fecha: 13/10/2026. La PC usó la IP fija 192.168.1.32 durante la prueba (§4.4 del informe explica por qué).

| Archivo | Qué muestra |
|---|---|
| server_20261013_161536.csv | CSV del servidor durante los dos cortes del punto de acceso |
| A08_OI1.log | Log del monitor serie de OI-1 |
| A08_OI2.log | Log del monitor serie de OI-2 |
| A08_analisis.txt | Salida de `analyze_log.py` para el CSV y los dos logs |
| A08.mp4 | LEDs durante los cortes: los tres parpadean sin red y vuelve el amarillo al volver la red |

| Corte | Placas detectan la caída (`wifi=down`) | Pedidos de red | OI-1 registrado de nuevo | OI-2 registrado de nuevo |
|---|---|---|---|---|
| 1 | 34.6 s | cada 9998–10002 ms | 135.3 s | 120.7 s |
| 2 | 200.8 s | cada 9998–10002 ms | 281.6 s | 291.0 s |

Tiempos en segundos desde el `START` del CSV. Las dos veces el sistema volvió a MEDIUM sin tocar ningún nodo, y ninguna placa se reinició.

Líneas `FAIL` en `A08_analisis.txt`:
- RNF1, RNF3 y RNF4: corresponden a los cortes provocados y a la inestabilidad de la red durante la prueba.
- `RF7 (c) connection attempts` (hasta 16 s): el script mide como un solo intervalo dos intentos separados por un `WIFI_RETRY`, porque la red se cayó otra vez mientras el router terminaba de arrancar. Con WiFi, los intentos fueron cada 1762–2000 ms.

A los 150.0 s el servidor perdió a la vez todas sus conexiones mientras las placas seguían con `wifi=up`, unos 50 s antes del segundo corte; se analiza en §4.4 del informe.