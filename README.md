# SecondProject-IoT: sensor de distancia y semáforo de LEDs por TCP

Un ESP32 con un sensor ultrasónico (OI-1) envía lecturas por WiFi a un servidor
TCP en Python, que decide la zona y ordena a un segundo ESP32 (OI-2) encender 3 LEDs.

- **Materia:** SIS-234 Internet de las Cosas, Práctica 2
- **Universidad:** Universidad Católica Boliviana "San Pablo"
- **Grupo 1:** Ricardo Andres Andrade Vargas · Dabner Eliezer Orozco Veizaga

> **Informe técnico completo: [Informe.md](Informe.md)**

## Carpetas

| Carpeta | Contenido |
|---|---|
| [src/sensor](src/sensor) | Firmware de OI-1: sensor ultrasónico y envío de lecturas |
| [src/actuator](src/actuator) | Firmware de OI-2: recepción de órdenes y control de los 3 LEDs |
| [lib](lib) | Código compartido por los dos firmwares |
| [include](include) | Plantilla de configuración de red ([Secrets.example.h](include/Secrets.example.h)) |
| [server](server) | Servidor TCP en Python, lógica de zonas y pruebas |
| [docs](docs) | Esquemas, imágenes y evidencias de las pruebas |

## Ejecución

1. Copiar `include/Secrets.example.h` como `include/Secrets.h` y completar la red WiFi y la IP de la PC.
2. Desde `server/`: `python tcp_server.py`.
3. Cargar los firmwares: `pio run -e sensor -t upload` y `pio run -e actuator -t upload`.
4. Pruebas, desde `server/`: `python -m unittest -v` y, con el servidor en marcha, `python -m tests.system_check`.
