# Contra Espacios · OLED UDP + sesiones

Interfaz local para Raspberry Pi con pantalla OLED I2C de 128x96, cinco botones físicos, comunicación UDP con Node-RED y manejo de sesiones persistentes en `~/data`.

Este módulo forma parte de **Contra Espacios** de **Amaranta Chikiframe**. La pantalla OLED permite controlar el flujo principal de captura y producción:

- capturar foto;
- capturar lectura ambiental;
- crear una nueva sesión;
- seleccionar una sesión anterior;
- generar dibujo;
- ejecutar dibujo;
- consultar estado.

La prioridad de esta versión es mantener el sistema reproducible en otra Raspberry Pi sin depender de una base de datos ni de archivos dentro del repositorio. Por eso los datos se guardan fuera del proyecto, en:

```text
~/data
```

Así se conservan aunque se actualice o reemplace el repositorio. Una rara victoria contra el caos, celebremos con moderación.

---

## 1. Hardware usado

### Raspberry Pi

Probado para una Raspberry Pi con I2C habilitado y GPIO disponibles.

### Pantalla OLED

Pantalla OLED I2C visible de **128x96 px**, con controlador compatible con SH1107/SH1106 en dirección:

```text
0x3C
```

Conexión:

```text
OLED VCC  -> 3.3V
OLED GND  -> GND
OLED SDA  -> GPIO2 / pin físico 3
OLED SCL  -> GPIO3 / pin físico 5
```

### Botonera de 5 botones

Los botones van entre GPIO y GND. El programa usa resistencias pull-up internas.

```text
GPIO ---- botón ---- GND
```

| Botón | Pin físico | GPIO | Acción |
|---|---:|---:|---|
| 1 | 11 | GPIO17 | Arriba / anterior |
| 2 | 13 | GPIO27 | Abajo / siguiente |
| 3 | 15 | GPIO22 | Seleccionar |
| 4 | 16 | GPIO23 | Volver |
| 5 | 18 | GPIO24 | Estado rápido |

---

## 2. Instalar dependencias en una Raspberry Pi nueva

Actualizar sistema:

```bash
sudo apt update
sudo apt upgrade -y
```

Instalar paquetes necesarios:

```bash
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  python3-lgpio \
  python3-gpiozero \
  python3-pil \
  python3-smbus \
  i2c-tools \
  git
```

Habilitar I2C:

```bash
sudo raspi-config
```

Entrar a:

```text
Interface Options -> I2C -> Enable
```

Reiniciar:

```bash
sudo reboot
```

Comprobar que la OLED aparece en I2C:

```bash
i2cdetect -y 1
```

Deberías ver algo como:

```text
3c
```

---

## 3. Crear entorno Python

Entrar a la carpeta del módulo OLED dentro del repositorio:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
```

Crear entorno virtual con acceso a paquetes del sistema:

```bash
python3 -m venv --system-site-packages .venv
```

Activar entorno:

```bash
source .venv/bin/activate
```

Instalar dependencias Python adicionales:

```bash
pip install pillow smbus2
```

`gpiozero` y `lgpio` se instalan desde `apt`, no desde `pip`, porque en Raspberry Pi eso evita una bonita colección de errores absurdos.

---

## 4. Ejecutar el programa

Desde la carpeta OLED:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

El programa crea automáticamente:

```text
~/data/state.json
~/data/sessions/S01/
~/data/sessions/S01/session.json
~/data/sessions/S01/photos/
~/data/sessions/S01/environment/
~/data/sessions/S01/output/
```

La primera sesión activa es `S01`.

---

## 5. Ruta persistente de datos

Por defecto:

```text
~/data
```

El archivo global:

```text
~/data/state.json
```

guarda la sesión activa:

```json
{
  "active_session": "S01",
  "last_session": "S01",
  "max_sessions": 64,
  "session_count": 1,
  "updated_at": "2026-06-21T05:28:00"
}
```

Las sesiones viven en:

```text
~/data/sessions/
```

Ejemplo:

```text
~/data/
├── state.json
└── sessions/
    ├── S01/
    │   ├── session.json
    │   ├── photos/
    │   ├── environment/
    │   └── output/
    └── S02/
        ├── session.json
        ├── photos/
        ├── environment/
        └── output/
```

Si necesitas usar otra ruta:

```bash
python3 oled-udp.py --data-root /ruta/persistente/data
```

---

## 6. Menú principal

El menú principal queda así:

```text
SES S01
> Capturar foto
  Capturar ambiente
  Nueva sesion
  Seleccionar sesion
  Generar dibujo
  Ejecutar dibujo
  Estado
```

Si la sesión activa ya tiene un dibujo generado, aparece con asterisco:

```text
SES S03*
```

El asterisco significa:

```text
esta sesión ya tiene dibujo generado
```

---

## 7. Manejo de sesiones

### Primera vez que arranca

Si no existe ninguna sesión, el programa crea:

```text
S01
```

y guarda todo ahí de forma predeterminada.

### Nueva sesión

La opción:

```text
Nueva sesion
```

crea el primer slot disponible entre `S01` y `S64`.

Ejemplo: si existen `S01`, `S02` y `S04`, creará `S03`.

Al crearla, actualiza:

```text
~/data/state.json
```

para que Node-RED y la OLED sepan cuál es la sesión activa.

### Seleccionar sesión

La opción:

```text
Seleccionar sesion
```

no muestra una lista larga. Muestra algo así:

```text
ELEGIR SESION
Sesion 03/12
ID: S03*
Fotos: 03
Amb:   03
Dib: OK
Sel: activar
Back: menu
```

`Sesion 03/12` significa:

```text
estás viendo la tercera carpeta encontrada de doce sesiones existentes
```

Al seleccionar, esa sesión queda activa y todo lo que se capture después debe guardarse ahí.

---

## 8. Pantalla de estado

La pantalla visible real es de 128x96 px, así que el estado está compactado:

```text
EST  50% done
Ses:S03*
Paso:ambiente
Msg:Ambiente listo
F:03 A:03
Dib:OK G:--
Ex:-- 05:28:34
```

Campos:

| Campo | Significado |
|---|---|
| `EST` | progreso general |
| `Ses` | sesión activa |
| `*` | sesión con dibujo ya generado |
| `Paso` | paso actual |
| `Msg` | último mensaje recibido |
| `F` | cantidad de fotos |
| `A` | cantidad de lecturas ambientales |
| `Dib` | dibujo generado |
| `G` | G-code generado |
| `Ex` | ejecución realizada |

---

## 9. Comunicación UDP

La OLED se comunica con Node-RED por UDP local.

### OLED -> Node-RED

```text
Host: 127.0.0.1
Puerto: 5005
```

### Node-RED -> OLED

```text
Host: 127.0.0.1
Puerto: 5006
```

Al arrancar, la OLED manda un `hello` a Node-RED:

```json
{
  "type": "hello",
  "message": "OLED interface online",
  "listen_port": 5006,
  "active_session": "S01",
  "session_id": "S01",
  "session_has_drawing": false,
  "data_root": "/home/pi/data"
}
```

---

## 10. Lo que manda la OLED a Node-RED

Cada comando incluye la sesión activa.

Ejemplo al capturar foto:

```json
{
  "type": "command",
  "command": "capture_photo",
  "label": "Capturar foto",
  "session_id": "S01",
  "active_session": "S01",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:28:00"
}
```

Ejemplo al pedir ambiente:

```json
{
  "type": "command",
  "command": "capture_environment",
  "label": "Capturar ambiente",
  "session_id": "S01",
  "active_session": "S01",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:29:00"
}
```

Node-RED debe usar `session_id` para decidir dónde guardar:

```text
~/data/sessions/S01/photos/
~/data/sessions/S01/environment/
~/data/sessions/S01/output/
```

---

## 11. Lo que Node-RED debe mandar a la OLED

### Progreso simple

```json
{
  "type": "status",
  "step": "environment",
  "state": "running",
  "message": "Gases 14s",
  "progress": 42
}
```

### Foto lista

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "photo": true,
  "photo_done": true,
  "photo_count": 1,
  "step": "photo",
  "state": "done",
  "message": "Foto guardada",
  "progress": 25
}
```

### Ambiente listo

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "environment": true,
  "environment_done": true,
  "environment_count": 1,
  "step": "environment",
  "state": "done",
  "message": "Ambiente listo",
  "progress": 50
}
```

### Dibujo generado

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "drawing": true,
  "drawing_done": true,
  "session_has_drawing": true,
  "step": "drawing",
  "state": "done",
  "message": "Dibujo generado",
  "progress": 75
}
```

### G-code generado

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "gcode": true,
  "gcode_done": true,
  "step": "gcode",
  "state": "done",
  "message": "G-code listo",
  "progress": 85
}
```

### Ejecución terminada

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "executed": true,
  "executed_done": true,
  "step": "execute",
  "state": "done",
  "message": "Ejecucion lista",
  "progress": 100
}
```

---

## 12. Configuración mínima de Node-RED

### Nodo UDP IN para recibir OLED

```text
Puerto: 5005
Output: string
```

Después conectar a:

```text
json
```

### Nodo UDP OUT para responder a OLED

```text
Host: 127.0.0.1
Puerto: 5006
```

El payload debe ser string JSON. En Function nodes usa:

```javascript
msg.payload = JSON.stringify(response);
```

No mandes objetos crudos directo al UDP de la OLED. Eso produce mensajes inválidos y la pantalla, con razón, entra en modo berrinche hexadecimal.

---

## 13. Node-RED y ESP32 ambiental

El ESP32 ambiental usa:

```text
Node-RED -> ESP32: contraenv.local:4210
ESP32 -> Node-RED: puerto 5010
```

Flujo sugerido:

```text
OLED UDP IN 5005
↓
json
↓
switch command == capture_environment
↓
function Solicitar lectura ambiente
├── salida 1 -> UDP OUT contraenv.local:4210
└── salida 2 -> UDP OUT 127.0.0.1:5006
```

Recepción del ESP32:

```text
UDP IN 5010
↓
json
↓
function Procesar respuesta ambiente
├── salida 1 -> datos para guardar o usar
└── salida 2 -> UDP OUT 127.0.0.1:5006
```

La salida 2 es la única que debe ir a la OLED.

---

## 14. Ejecutar como servicio systemd

Crear servicio:

```bash
sudo nano /etc/systemd/system/contra-oled.service
```

Contenido, ajustando el usuario si no es `pi`:

```ini
[Unit]
Description=Contra Espacios OLED UDP Interface
After=nodered.service network-online.target
Wants=network-online.target
Requires=nodered.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Documents/GitHub/contraespacios/OLED
ExecStart=/home/pi/Documents/GitHub/contraespacios/OLED/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/OLED/oled-udp.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable contra-oled.service
sudo systemctl start contra-oled.service
```

Ver estado:

```bash
systemctl status contra-oled.service
```

Ver logs:

```bash
journalctl -u contra-oled.service -f
```

Si usas otro usuario, cambia:

```text
User=pi
/home/pi/
```

por tu usuario real.

---

## 15. Probar UDP manualmente

Escuchar lo que manda OLED:

```bash
nc -ul 5005
```

Mandar un estado manual a la OLED:

```bash
echo '{"type":"status","step":"environment","state":"running","message":"Prueba OLED","progress":42}' | nc -u -w1 127.0.0.1 5006
```

Marcar ambiente como listo:

```bash
echo '{"type":"framework_state","session_id":"S01","environment":true,"environment_done":true,"environment_count":1,"step":"environment","state":"done","message":"Ambiente listo","progress":50}' | nc -u -w1 127.0.0.1 5006
```

Marcar dibujo generado con asterisco de sesión:

```bash
echo '{"type":"framework_state","session_id":"S01","drawing":true,"drawing_done":true,"session_has_drawing":true,"step":"drawing","state":"done","message":"Dibujo generado","progress":75}' | nc -u -w1 127.0.0.1 5006
```

---

## 16. Archivos incluidos

```text
OLED/
├── oled-udp.py
├── README.md
└── OLED_UDP_mensajes_completo.md
```

