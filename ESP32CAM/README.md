# ESP32CAM - Contra Espacios

Esta carpeta contiene los programas para los microcontroladores del sistema **Contra Espacios** relacionados con captura de imagen y lectura ambiental.

Hay dos bloques principales:

- **ESP32CAM / ContraCam**: cámara web local basada en el ejemplo `CameraWebServer` de ESP32/Espressif.
- **ESP32 DevKit V1 + ENS160/AHT21**: lectura de sensores ambientales, con versión simple por monitor serial y versión MQTT para Node-RED.

---

## 1. Estructura de la carpeta

Contenido esperado de la carpeta `ESP32CAM`:

```text
ESP32CAM/
├── contracam.ino
├── CameraWebServer.ino
├── app_httpd.cpp
├── board_config.h
├── camera_index.h
├── camera_pins.h
├── partitions.csv
├── ci.yml
├── 01_Simple_ENS160_AHT21.ino
├── 02_MQTT_ENS160_AHT21.ino
└── README.md
```

También pueden existir copias generadas por descargas o pruebas anteriores con nombres como:

```text
app_httpd(1).cpp
app_httpd(2).cpp
board_config(1).h
board_config(2).h
camera_pins(1).h
camera_pins(2).h
README(12).md
README(13).md
```

Para el repo final conviene limpiar esos duplicados y conservar solo los archivos con nombre limpio.

---

## 2. Programas principales

| Archivo | Uso |
|---|---|
| `contracam.ino` | Programa recomendado para la ESP32CAM. Usa hostname, mDNS, arranque en 640x480 y reinicio si pierde WiFi. |
| `CameraWebServer.ino` | Versión base del ejemplo de Espressif. Se conserva como referencia. |
| `app_httpd.cpp` | Servidor HTTP de la cámara. Define endpoints como `/`, `/capture` y stream. |
| `board_config.h` | Selección del modelo de cámara. Actualmente se usa AI Thinker. |
| `camera_pins.h` | Pines de los distintos modelos de cámara ESP32CAM. |
| `camera_index.h` | Página web embebida del servidor de cámara. |
| `partitions.csv` | Esquema de particiones para permitir sketches grandes. |
| `01_Simple_ENS160_AHT21.ino` | Prueba simple del sensor ENS160+AHT21 por monitor serial. |
| `02_MQTT_ENS160_AHT21.ino` | Lectura ambiental con envío MQTT para Node-RED. |

---

# Bloque A - ContraCam ESP32CAM

## 3. Qué hace `contracam.ino`

`contracam.ino` es el sketch recomendado para usar la ESP32CAM en el sistema.

Agrega:

- Hostname local: `contracam`.
- mDNS: `http://contracam.local`.
- Captura JPG: `http://contracam.local/capture`.
- Stream MJPEG: `http://contracam.local:81/stream`.
- Arranque en resolución VGA: `640x480`.
- Reinicio automático si no logra conectarse al WiFi.
- Reinicio automático si pierde WiFi durante más de 30 segundos.
- Mensajes por monitor serial con IP, hostname y URLs.

Esto permite que la Raspberry Pi encuentre la cámara sin depender de una IP fija.

La vida ya es suficientemente indigna como para además perseguir direcciones DHCP a mano.

---

## 4. Configuración WiFi de ContraCam

En `contracam.ino` se usan estas constantes:

```cpp
const char *ssid = "contraespacios";
const char *password = "cinemabarredura";
const char *hostName = "contracam";
```

Para desarrollo rápido, configura el hotspot del teléfono o router con:

```text
Nombre WiFi: contraespacios
Contraseña: cinemabarredura
```

La Raspberry Pi y la ESP32CAM deben estar conectadas a la misma red.

---

## 5. URLs de ContraCam

Cuando la ESP32CAM arranca correctamente, debe ser accesible desde la Raspberry Pi como:

```text
http://contracam.local
```

Captura JPG:

```text
http://contracam.local/capture
```

Stream MJPEG:

```text
http://contracam.local:81/stream
```

Si `contracam.local` no resuelve, revisar la IP que aparece en el monitor serial y probar con:

```text
http://IP_DE_LA_ESP32CAM/capture
```

---

## 6. Probar ContraCam desde Raspberry Pi

Instalar soporte mDNS/Avahi:

```bash
sudo apt update
sudo apt install -y avahi-daemon avahi-utils
sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon
```

Probar resolución:

```bash
ping contracam.local
```

o:

```bash
avahi-resolve -n contracam.local
```

Capturar una imagen:

```bash
curl http://contracam.local/capture --output foto.jpg
```

Probar la página principal:

```bash
curl http://contracam.local
```

Ver headers de captura:

```bash
curl -I http://contracam.local/capture
```

---

## 7. Configuración Arduino IDE para ESP32CAM

Seleccionar:

```text
Board: AI Thinker ESP32-CAM
PSRAM: Enabled
Partition Scheme: Huge APP o esquema con al menos 3MB para APP
Upload Speed: 115200 o 921600
```

Si el sketch no cabe, usar el archivo:

```text
partitions.csv
```

o seleccionar un esquema de partición más grande desde el menú de Arduino IDE.

---

## 8. Monitor serial de ContraCam

Abrir monitor serial a:

```text
115200 baudios
```

Salida esperada:

```text
WiFi connected
Camera Ready!
IP: 192.168.x.x
Hostname DHCP: contracam
mDNS URL: http://contracam.local
Capture:  http://contracam.local/capture
Stream:   http://contracam.local:81/stream
```

---

## 9. Hotspot Android o iPhone

### Android

Normalmente es viable:

```text
Android hotspot
├── Raspberry Pi
└── ESP32CAM
```

Si ambos dispositivos pueden verse entre sí, `contracam.local` debería funcionar.

### iPhone

Puede funcionar, pero es menos confiable. Algunos hotspots aíslan clientes o limitan tráfico local.

Si `contracam.local` no responde:

```bash
avahi-browse -a
ping contracam.local
curl http://contracam.local/capture --output foto.jpg
```

Si no responde por nombre, probar por IP. Si tampoco responde por IP, probablemente el hotspot está bloqueando comunicación entre clientes.

---

## 10. Uso desde Node-RED

En Node-RED, usar un nodo HTTP request:

```text
GET http://contracam.local/capture
```

El resultado será una imagen JPG.

Para guardar la imagen:

1. Nodo `http request`.
2. Nodo `file`.
3. Guardar como archivo `.jpg`.

Ejemplo de ruta:

```text
/home/pi/Documents/GitHub/contraespacios/data/foto.jpg
```

---

# Bloque B - Sensor ENS160 + AHT21

## 11. Hardware del sensor ambiental

El sensor ambiental usa:

- ESP32 DevKit V1 o compatible.
- Módulo ENS160 + AHT21.

Conexión:

```text
ENS160+AHT21    ESP32 DevKit V1
-------------------------------
VCC ----------> 3.3V
GND ----------> GND
SDA ----------> GPIO21
SCL ----------> GPIO22
```

---

## 12. Bibliotecas necesarias

Instalar desde Arduino IDE:

```text
SparkFun ENS160 Arduino Library
Adafruit AHTX0
PubSubClient
ArduinoJson
```

---

## 13. Prueba simple del sensor

Archivo:

```text
01_Simple_ENS160_AHT21.ino
```

Este programa:

- inicia I2C en GPIO21/GPIO22;
- escanea dispositivos I2C;
- detecta AHT2x;
- detecta ENS160 en `0x53` y si falla prueba `0x52`;
- muestra temperatura, humedad, AQI, TVOC y eCO2 en el monitor serial.

Monitor serial:

```text
115200 baudios
```

Salida esperada:

```text
T=25.00 C  RH=45.00 %  |  AQI=1  TVOC=100 ppb  eCO2=500 ppm
```

---

## 14. Programa MQTT del sensor

Archivo:

```text
02_MQTT_ENS160_AHT21.ino
```

Este programa:

- conecta el ESP32 a WiFi;
- lee temperatura, humedad, AQI, TVOC y eCO2;
- publica un JSON por MQTT cada 30 segundos;
- está pensado para ser recibido por Node-RED.

Configuración actual en el archivo:

```cpp
const char* WIFI_SSID = "cinema";
const char* WIFI_PASS = "barredura";
const char* MQTT_HOST = "192.168.1.105";
const uint16_t MQTT_PORT = 1883;
const char* MQTT_TOPIC = "ambiente/lectura";
```

---

## 15. Ajuste recomendado para desarrollo actual

Si estás usando el mismo hotspot que ContraCam, puedes cambiar en `02_MQTT_ENS160_AHT21.ino`:

```cpp
const char* WIFI_SSID = "contraespacios";
const char* WIFI_PASS = "cinemabarredura";
```

El host MQTT debe apuntar a la Raspberry Pi.

Si la Raspberry cambia de IP por hotspot, hay tres opciones:

| Opción | Uso |
|---|---|
| IP actual de la Raspberry | Rápido para pruebas |
| Raspberry como punto de acceso final | Mejor para instalación final |
| mDNS para broker MQTT | Posible, pero requiere ajustar el ESP32 para resolver hostname |

Para pruebas rápidas, puedes ver la IP de la Raspberry con:

```bash
hostname -I
```

Y poner esa IP en:

```cpp
const char* MQTT_HOST = "IP_DE_LA_RASPBERRY";
```

Ejemplo:

```cpp
const char* MQTT_HOST = "172.20.10.4";
```

---

## 16. Payload MQTT enviado

El programa publica en:

```text
ambiente/lectura
```

Payload esperado:

```json
{
  "temperatura": 25.30,
  "humedad": 44.20,
  "aqi": 1,
  "tvoc": 100,
  "eco2": 500
}
```

Si la lectura falla, manda valores `null`:

```json
{
  "temperatura": null,
  "humedad": null,
  "aqi": null,
  "tvoc": null,
  "eco2": null
}
```

---

## 17. Probar MQTT en Raspberry Pi

Si usas Mosquitto en la Raspberry:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
```

Escuchar el topic:

```bash
mosquitto_sub -h localhost -t ambiente/lectura -v
```

Si el ESP32 está publicando correctamente, verás algo como:

```text
ambiente/lectura {"temperatura":25.30,"humedad":44.20,"aqi":1,"tvoc":100,"eco2":500}
```

---

## 18. Uso del sensor en Node-RED

En Node-RED:

| Nodo | Configuración |
|---|---|
| `mqtt in` | Broker: Raspberry Pi / Topic: `ambiente/lectura` |
| `json` | Convierte payload a objeto |
| `function` | Limpia, guarda o transforma datos |
| `mysql` | Guarda datos en base de datos, si aplica |
| `dashboard` | Muestra datos en interfaz, si aplica |

---

# Bloque C - Flujo general del framework

## 19. Relación entre ESP32CAM, sensor, Raspberry y Node-RED

```text
ESP32CAM / ContraCam
    │
    │ HTTP GET /capture
    ▼
Raspberry Pi / Node-RED
    │
    ├── guarda foto JPG
    ├── lee datos ambientales por MQTT
    ├── genera SVG
    ├── genera G-code
    └── manda G-code a GRBL

ESP32 DevKit + ENS160/AHT21
    │
    │ MQTT ambiente/lectura
    ▼
Raspberry Pi / Node-RED
```

---

## 20. Prueba completa mínima

### 1. Encender hotspot

Usar:

```text
SSID: contraespacios
Password: cinemabarredura
```

### 2. Conectar Raspberry Pi al hotspot

Confirmar IP:

```bash
hostname -I
```

### 3. Encender ESP32CAM

Probar:

```bash
ping contracam.local
curl http://contracam.local/capture --output foto.jpg
```

### 4. Encender ESP32 del sensor

Si el MQTT usa IP, confirmar que `MQTT_HOST` apunte a la Raspberry.

Escuchar datos:

```bash
mosquitto_sub -h localhost -t ambiente/lectura -v
```

### 5. Usar Node-RED

Abrir:

```text
http://127.0.0.1:1880/
```

---

## 21. Problemas comunes

### `contracam.local` no responde

Revisar:

```bash
systemctl status avahi-daemon
avahi-browse -a
ping contracam.local
```

Si falla por nombre, probar por IP desde monitor serial.

### La cámara no se conecta

Revisar:

- SSID.
- Contraseña.
- Que la red sea 2.4 GHz.
- Alimentación estable de la ESP32CAM.
- Monitor serial a 115200.

### La foto falla o sale incompleta

Revisar:

- PSRAM habilitada.
- Placa correcta: AI Thinker ESP32-CAM.
- Partición con suficiente espacio.
- Alimentación de 5V estable.

### MQTT no llega

Revisar:

```bash
systemctl status mosquitto
mosquitto_sub -h localhost -t ambiente/lectura -v
```

Revisar que `MQTT_HOST` sea la IP actual de la Raspberry Pi.

### Node-RED no ve datos

Revisar:

- Topic `ambiente/lectura`.
- Nodo `mqtt in`.
- Nodo `json`.
- Broker configurado como `localhost` si Mosquitto corre en la Raspberry.

---

## 22. Limpieza sugerida del repo

Para evitar confusión, conservar una sola copia de cada archivo:

```text
ESP32CAM/
├── contracam.ino
├── app_httpd.cpp
├── board_config.h
├── camera_index.h
├── camera_pins.h
├── partitions.csv
├── ci.yml
├── 01_Simple_ENS160_AHT21.ino
├── 02_MQTT_ENS160_AHT21.ino
└── README.md
```

Mover o eliminar archivos duplicados con nombres como:

```text
app_httpd(1).cpp
app_httpd(2).cpp
camera_pins(1).h
camera_pins(2).h
README(12).md
README(13).md
```

No porque sean malignos, sino porque Arduino IDE es perfectamente capaz de convertir duplicados inocentes en una tarde perdida. Qué sorpresa.

---

## 23. Estado actual

- [x] ContraCam probada.
- [x] `contracam.local` funcional.
- [x] Captura HTTP disponible.
- [x] Resolución inicial 640x480.
- [x] Reinicio por pérdida de WiFi.
- [x] Sensor ENS160+AHT21 documentado.
- [x] MQTT ambiental documentado.
- [ ] Ajustar `MQTT_HOST` según red real de la Raspberry.
- [ ] Integrar captura de ContraCam en Node-RED.
- [ ] Integrar datos ambientales MQTT en Node-RED.
- [ ] Conectar ambos datos al generador del framework.
