# Evidencia B01: Pruebas unitarias del algoritmo de control

Prueba B01 de la sección 4.3 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra |
|---|---|
| B01_salida.txt | Salida de `python -m unittest -v`, ejecutado desde `server/`, con las 17 pruebas de `server/tests/test_zone_controller.py` |

| Clase de prueba | Casos | Resultado |
|---|---|---|
| `ClassifyTest` | 5 | 5 `ok` |
| `HysteresisTest` | 7 | 7 `ok` |
| `InvalidReadingTest` | 4 | 4 `ok` |
| `CommandTest` | 1 | 1 `ok` |

Resumen final: `Ran 17 tests in 0.001s` y `OK`.