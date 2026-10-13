# Evidencia A05: Tiempo de respuesta extremo a extremo

Prueba A05 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra | Caso |
|---|---|---|
| server_20261013_141946.csv | Tarjeta insertada y retirada de golpe a unos 10 cm, con la pared a 111.6 cm: cambios FAR ↔ NEAR | A05-A |
| server_20261013_142028.csv | Tarjeta insertada y retirada de golpe a unos 30 cm, con la pared a 112.2 cm: cambios FAR ↔ MEDIUM | A05-B |
| A05_salida.txt | Salida de `analyze_log.py` para los dos CSV | A05-A, A05-B |
| A05-A.mp4 | LEDs durante A05-A: el blanco fijo y el rojo parpadeando se alternan | A05-A |
| A05-B.mp4 | LEDs durante A05-B: el blanco fijo y el amarillo parpadeando se alternan | A05-B |

Tiempo de respuesta (100 ms + `latency_ms`, reloj del servidor):

| Serie | Cambios de zona | `latency_ms` mín. | Mediana | Percentil 95 | Máx. | Peor respuesta | Veredicto |
|---|---|---|---|---|---|---|---|
| A05-A, FAR ↔ NEAR | 19 | 11.1 ms | 16.2 ms | 60.4 ms | 60.4 ms | 160.4 ms | PASS |
| A05-B, FAR ↔ MEDIUM | 23 | 8.9 ms | 18.5 ms | 44.8 ms | 140.8 ms | 240.8 ms | PASS |

El máximo de A05-B (140.8 ms) es el cambio inicial ERROR → FAR, recién conectado OI-2. Las lecturas sueltas de 129.7 cm (A05-A, seq 2126) y 141.8 cm (A05-B, seq 2454) se analizan en §4.4 del informe.