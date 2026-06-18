# ContraCam - ESP32CAM para Contra Espacios

Este sketch deriva del ejemplo `CameraWebServer` de ESP32/Espressif y queda ajustado para el proyecto **Contra Espacios**.

La idea es que la Raspberry Pi pueda encontrar la ESP32CAM sin depender de una IP fija, incluso cuando se use un hotspot de Android/iPhone o una red temporal.

---

## 1. Qué corrige esta versión

Esta versión agrega:

- Hostname local: `contracam`.
- mDNS: `http://contracam.local`.
- Arranque en resolución VGA: `640x480`.
- Reinicio automático si no puede conectarse al WiFi.
- Reinicio automático si pierde WiFi durante más de 30 segundos.
- Mensajes seriales claros con IP, hostname y URLs.
- Configuración lista para AI Thinker ESP32CAM.

---

## 2. Archivos incluidos

```text
contracam/
├── contracam.ino
├── app_httpd.cpp
├── board_config.h
├── camera_index.h
├── camera_pins.h
├── partitions.csv
├── ci.yml
└── README.md
```

---

## 3. Configuración WiFi

En `contracam.ino` están estas líneas:

```cpp
const char *ssid = "contraespacios";
const char *password = "cinemabarredura";
const char *hostName = "contracam";
```

Para desarrollo rápido puedes hacer una de estas dos cosas:

- Crear un hotspot llamado `contraespacios` con contraseña `cinemabarredura`.
- Cambiar `ssid` y `password` en el código por los de la red disponible.

El hostname recomendado es:

```text
contracam
```

La Raspberry debería poder verla como:

```text
contracam.local
```

---

## 4. URLs esperadas

Cuando la ESP32CAM arranque correctamente, puedes usar:

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

Si mDNS no funciona, en el monitor serial también aparecerá la IP asignada por el router o hotspot.

---

## 5. Resolución inicial

Esta versión fuerza la resolución inicial a:

```text
640x480
```

En el código corresponde a:

```cpp
FRAMESIZE_VGA
```

Se aplica en dos lugares:

```cpp
config.frame_size = FRAMESIZE_VGA;
```

y después de iniciar la cámara:

```cpp
s->set_framesize(s, FRAMESIZE_VGA);
```

Esto evita que el ejemplo original baje automáticamente a `QVGA`.

---

## 6. Reinicio por pérdida de WiFi

El programa revisa WiFi cada 5 segundos.

```cpp
const unsigned long WIFI_CHECK_INTERVAL_MS = 5000;
```

Si pierde conexión durante más de 30 segundos, reinicia:

```cpp
const unsigned long WIFI_LOST_RESTART_MS = 30000;
```

Esto evita que la ESP32CAM quede viva pero desconectada, ese estado inútil que tanto ama el hardware embebido.

---

## 7. mDNS en la Raspberry Pi

Para resolver `contracam.local`, la Raspberry Pi necesita soporte mDNS/Avahi.

Instalar:

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

Probar captura:

```bash
curl http://contracam.local/capture --output foto.jpg
```

---

## 8. Si usas hotspot de Android o iPhone

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

1. Revisar IP por monitor serial.
2. Probar `ping` a la IP.
3. Probar `curl http://IP/capture`.
4. Si tampoco responde por IP, el hotspot está bloqueando comunicación entre clientes.

---

## 9. Configuración en Arduino IDE

Seleccionar una placa compatible con ESP32CAM AI Thinker.

Configuración típica:

```text
Board: AI Thinker ESP32-CAM
Partition Scheme: Huge APP o una partición con al menos 3MB para APP
PSRAM: Enabled
Upload Speed: 115200 o 921600
```

Si aparece problema de tamaño de sketch, usar el archivo `partitions.csv` o seleccionar un esquema con más espacio.

---

## 10. Monitor serial

Abrir monitor serial a:

```text
115200 baudios
```

Al arrancar debe mostrar algo parecido:

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

## 11. Uso desde Raspberry Pi

Capturar foto:

```bash
curl http://contracam.local/capture --output foto.jpg
```

Ver headers:

```bash
curl -I http://contracam.local/capture
```

Probar página principal:

```bash
curl http://contracam.local
```

---

## 12. Uso desde Node-RED

En Node-RED puedes usar un nodo HTTP request con:

```text
GET http://contracam.local/capture
```

El resultado será una imagen JPG.

Para guardar la imagen, usar un nodo `file`.

---

## 13. Si mDNS no resuelve

Probar en Raspberry:

```bash
avahi-browse -a
```

Buscar algo relacionado con:

```text
contracam
```

También probar:

```bash
ping contracam.local
```

Si falla, revisar:

- que ESP32CAM y Raspberry estén en la misma red,
- que el hotspot no bloquee clientes,
- que Avahi esté corriendo,
- que la ESP32CAM haya iniciado mDNS,
- que la ESP32CAM esté realmente conectada al WiFi.

Ver estado de Avahi:

```bash
systemctl status avahi-daemon
```

Reiniciar Avahi:

```bash
sudo systemctl restart avahi-daemon
```

---

## 14. Cambios técnicos principales

En `contracam.ino` se agregó:

```cpp
#include <ESPmDNS.h>
```

Se estableció hostname antes de iniciar WiFi:

```cpp
WiFi.setHostname(hostName);
WiFi.begin(ssid, password);
```

Se inició mDNS:

```cpp
MDNS.begin(hostName);
MDNS.addService("http", "tcp", 80);
MDNS.addService("mjpeg", "tcp", 81);
```

Se agregó vigilancia WiFi:

```cpp
checkWiFiOrRestart();
```

Y se fuerza VGA:

```cpp
FRAMESIZE_VGA
```

---

## 15. Estado de esta versión

- [x] Hostname `contracam`.
- [x] mDNS `contracam.local`.
- [x] Resolución inicial 640x480.
- [x] Reinicio si no conecta a WiFi.
- [x] Reinicio si pierde WiFi.
- [x] Lista para capturar desde Raspberry Pi.
- [x] Lista para integrarse con Node-RED.
