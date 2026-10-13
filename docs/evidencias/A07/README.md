# Evidencia A07: Pérdida del sensor

Prueba A07 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| server_20261013_155524.csv | CSV del servidor: blanco a unos 18 cm (NEAR), dos desconexiones del USB de OI-1 y un reinicio con el botón EN |
| A07_analisis.txt | Salida de `analyze_log.py` para el CSV |
| A07.mp4 | LEDs durante la prueba: los tres parpadean mientras OI-1 no está y vuelve el rojo al reconectarse |

| Evento | Pérdida (`SENSOR/timeout`) tras la última lectura | `ACK 0` del ERROR | OI-1 registrado de nuevo tras su última lectura | Vuelta a NEAR |
|---|---|---|---|---|
| USB desconectado 1 | 1014 ms | 1041 ms | 7.1 s | seq 24, 18.4 cm |
| USB desconectado 2 | 1006 ms | 1187 ms | 9.9 s | seq 24, 18.7 cm |
| Botón EN | 1010 ms | 1033 ms | 3.1 s | seq 24, 18.1 cm |

RF7 (a) pide el ERROR en OI-2 en ≤ 1500 ms: las tres pérdidas cumplen. Las líneas `FAIL` de RNF1 y RNF4 en `A07_analisis.txt` corresponden a las pausas provocadas por la prueba.