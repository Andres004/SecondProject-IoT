# Evidencia A01: Arranque y funcionamiento por zona

Prueba A01 de la sección 4.2 del informe. Fecha: 13/10/2026.

| Archivo | Qué muestra | Caso |
|---|---|---|
| A01-A_arranque_error.mp4 | OI-2 conectado sin sensor: los tres LEDs parpadean juntos (ERROR) | A01-A |
| A01-A_consola_servidor.png | Consola del servidor: REGISTER ACTUATOR, SET 0 ALL BLINK y ACK 0 | A01-A |
| A01-A_log_oi2.png | Monitor serie de OI-2: TX REGISTER ACTUATOR, RX OK, RX SET 0 ALL BLINK y TX ACK 0 | A01-A |
| server_20261013_102843.csv | Registro de OI-2 sin sensor y, después, de OI-1 | A01-A |
| A01-B_near_rojo.mp4 | Blanco cerca: solo el LED rojo parpadea; consola con zone=NEAR | A01-B |
| A01-B_medium_amarillo.mp4 | Blanco a distancia media: solo el amarillo parpadea; zone=MEDIUM | A01-B |
| A01-B_far_blanco.mp4 | Blanco lejos: solo el blanco, encendido fijo; zone=FAR | A01-B |
| server_20261013_103320.csv | Zona NEAR estable | A01-B |
| server_20261013_103410.csv | Desconexión de OI-1 y cambios NEAR, MEDIUM y FAR con su SET y su ACK | A01-B, A01-C |
| server_20261013_111340.csv | Cambios entre las tres zonas | A01-B |
| A01-C_conteo_rojo.mp4 | LED rojo: 20 destellos en 10 s (2 Hz) | A01-C |
| A01-C_conteo_amarillo.mp4 | LED amarillo: 20 destellos en 10 s (2 Hz) | A01-C |
| A01-C_conteo_blanco.mp4 | En FAR el LED blanco queda encendido fijo durante 10 s | A01-C |
| A01-C_error_desconexion.mp4 | Al desconectar OI-1, los tres LEDs parpadean juntos: 20 destellos en 10 s | A01-C |
| A01-C_error_reconexion.mp4 | Al reconectar OI-1, el sistema vuelve a su zona | A01-C |
