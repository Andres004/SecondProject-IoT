# Evidencia A03: Límites del rango de medición

Prueba A03 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra | Caso |
|---|---|---|
| server_20261013_131202.csv | Primera ejecución, con el límite en 400 cm: lecturas continuas hasta unos 190 cm, muchas `NAN` más lejos y ninguna lectura válida a 400 cm. Es la medición que llevó a fijar el límite en 200 cm | Origen del límite |
| server_20261013_132637.csv | Segunda ejecución, con el límite en 200 cm: todos los casos de la prueba | A03-A, A03-B, A03-C |
| A03-A_2cm.mp4 | Objeto a 2 cm: el sistema empieza a medir y el LED rojo parpadea (NEAR) | A03-A |
| A03-B_150cm.mp4 | Objeto en la marca de 150 cm: LED blanco fijo (FAR) | A03-B |
| A03-B_190cm.mp4 | Objeto en la marca de 190 cm: LED blanco fijo (FAR) | A03-B |
| A03-B_200cm.mp4 | Objeto en la marca de 200 cm: LED blanco fijo (FAR) | A03-B |
| A03-B_mas_de_200cm.mp4 | Objeto más allá de 200 cm: los tres LEDs parpadean (ERROR) | A03-B, A03-C |

Lecturas usadas en cada distancia (CSV server_20261013_132637.csv, 10 seguidas con el objeto quieto):

| Distancia | seq | Lecturas | Zona |
|---|---|---|---|
| 2 cm | 2760–2769 | 2.3 cm | NEAR |
| 150 cm | 3200–3209 | 143.5 cm | FAR |
| 190 cm | 3420–3429 | 184.5–184.9 cm | FAR |
| 200 cm | 3550–3559 | 193.3–193.8 cm | FAR |
| Más de 200 cm | 3663–3752 | 205.2–258.0 cm y NAN (inválidas) | ERROR |
