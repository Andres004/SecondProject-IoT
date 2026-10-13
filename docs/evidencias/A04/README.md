# Evidencia A04: Histéresis con el sensor real

Prueba A04 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra | Caso |
|---|---|---|
| server_20261013_135158.csv | Blanco quieto en la frontera de 20 cm durante 55.5 s | A04-A |
| server_20261013_135325.csv | Blanco quieto en la frontera de 40 cm durante 49.1 s | A04-A |
| server_20261013_135541.csv | Cruce lento de 10 a 30 cm y de vuelta a 10 cm | A04-B |
| server_20261013_140622.csv | Cruce lento de 28 a 50 cm y de vuelta a 30 cm | A04-B |
| server_20261013_135958.csv | Primer intento del cruce de 40 cm, con lecturas sueltas de la mano en el haz; no cumple el criterio y se repitió (§4.4) | A04-B, intento descartado |
| A04-A_20cm.mp4 | Blanco quieto en 20 cm: el LED rojo parpadea todo el tiempo (NEAR) | A04-A |
| A04-A_40cm.mp4 | Blanco quieto en 40 cm: el LED amarillo parpadea todo el tiempo (MEDIUM) | A04-A |
| A04-B_cruce_20cm.mp4 | Cruce de la frontera de 20 cm: un solo cambio de LED en cada sentido | A04-B |
| A04-B_cruce_40cm.mp4 | Cruce de la frontera de 40 cm: un solo cambio de LED en cada sentido | A04-B |

Blanco quieto en cada frontera (A04-A):

| Frontera | CSV | seq | Duración | Lecturas | Zona | `SET` |
|---|---|---|---|---|---|---|
| 20 cm | 135158 | 2630–3185 | 55.5 s | 556, de 18.1 a 20.8 cm (15 ≥ 20.0 cm) | NEAR | 0 |
| 40 cm | 135325 | 3519–4003 | 49.1 s | 485, de 37.8 a 41.6 cm más una suelta de 31.3 cm (346 ≥ 40.0 cm) | MEDIUM | 0 |

Cambios de zona en los cruces (A04-B):

| Cruce | CSV | seq | Lectura | Cambio | Umbral |
|---|---|---|---|---|---|
| 20 cm, subida | 135541 | 4855 | 22.3 cm | NEAR → MEDIUM | ≥ 22.0 |
| 20 cm, bajada | 135541 | 5159 | 17.9 cm | MEDIUM → NEAR | < 18.0 |
| 40 cm, subida | 140622 | 304 | 42.1 cm | MEDIUM → FAR | ≥ 42.0 |
| 40 cm, bajada | 140622 | 523 | 37.8 cm | FAR → MEDIUM | < 38.0 |

El último cambio de 135541 (seq 5417, 29.0 cm, NEAR → MEDIUM) ocurre al llevar el blanco de golpe a unos 30 cm después del cruce; no es parte de la prueba.