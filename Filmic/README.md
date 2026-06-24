# Contra Espacios

Sistema portátil para capturar una sesión, generar un dibujo a partir de fotos y ambiente, convertirlo a G-code y ejecutarlo en una máquina de dibujo controlada por GRBL.

El proyecto usa una Raspberry Pi como centro de control, una pantalla OLED con botones como interfaz local, Node-RED como orquestador, módulos ESP32 para cámara/ambiente, un Arduino Uno con CNC Shield y una carpeta persistente de datos en:

```text
/home/pi/data
```

Las fotos, lecturas, metadatos, SVG, previews y G-code se guardan como archivos por sesión.

## Flujo Actual

```text
OLED + botones
→ Node-RED por UDP 5005
→ captura foto / ambiente
→ Drawing genera SVG, preview, process_steps y drawing.gcode
→ Filmic ejecuta drawing.gcode en GRBL
→ OLED muestra estado y progreso
```

## Estructura De Sesiones

Cada sesión vive fuera del repositorio:

```text
/home/pi/data/sessions/<SESSION_ID>/
├── photos/
├── environment/
└── output/
```

Ejemplo:

```text
/home/pi/data/sessions/S01/
├── photos/
│   └── photo_001.jpg
├── environment/
│   └── env_001.json
└── output/
    ├── drawing.svg
    ├── drawing.gcode
    ├── preview.png
    ├── metadata.json
    ├── generation_log.json
    └── process_steps/
```

## Módulos

### `OLED/`

Interfaz local en Raspberry Pi:

- pantalla OLED I2C 128x96;
- cinco botones físicos;
- envío de comandos a Node-RED por UDP `5005`;
- recepción de estado desde Node-RED por UDP `5006`;
- manejo de sesión activa.

### `Node-Red/`

Orquestador del sistema:

- recibe comandos desde la OLED;
- coordina captura de foto;
- solicita lectura ambiental;
- ejecuta `Drawing/generate_drawing.py`;
- ejecuta `Filmic/execute_drawing.py`;
- responde a la OLED con estado, conteos y progreso.

### `Drawing/`

Motor de generación:

- lee fotos y lecturas ambientales desde `/home/pi/data`;
- genera `drawing.svg`;
- genera `preview.png`;
- guarda `process_steps/`;
- genera `drawing.gcode`;
- responde con JSON para Node-RED.

`Drawing` no mueve la máquina. Solo genera archivos.

### `Filmic/`

Ejecutor de dibujo:

- lee `drawing.gcode` ya generado por `Drawing`;
- conecta con GRBL por USB;
- puede hacer homing;
- puede establecer cero de trabajo;
- transmite el G-code;
- reporta progreso por stdout para Node-RED/OLED.

`Filmic` no analiza fotos, no genera SVG y no genera G-code.

## Calibración Física Del Área

`Filmic` puede verificar físicamente los dos extremos de cada eje antes de ejecutar el dibujo.

Flujo:

1. Hace homing con `$H`.
2. Pone cero temporal en home.
3. Avanza X hasta detectar `Pn:X`.
4. Regresa a home.
5. Avanza Y hasta detectar `Pn:Y`.
6. Regresa a home.
7. Guarda el área útil en `/home/pi/data/machine/calibration.json`.
8. Valida que `drawing.gcode` quepa dentro de esa área.
9. Ejecuta el dibujo si todo está dentro de límites.

Durante esta calibración se recomienda mantener los hard limits apagados:

```text
$21=0
```

Los sensores siguen apareciendo en el estado `Pn:X` y `Pn:Y`, pero GRBL no entra en alarma al tocarlos durante el barrido.

### `GRBL/`

Firmware y documentación para Arduino Uno + CNC Shield:

- GRBL 1.1h;
- homing X/Y sin eje Z;
- sensores de límite;
- configuración por comandos `$`.

### `ESP32CAM/`

Programas para cámara y ambiente:

- ContraCam por HTTP;
- ENS160/AHT por UDP;
- pruebas simples de sensores.

### `RaspberryPi/`

Notas de instalación base para Raspberry Pi:

- sistema;
- Node.js / Node-RED;
- Python;
- dependencias de módulos;
- permisos seriales.

## Estado De La Máquina

El sistema de movimiento usa:

- Arduino Uno;
- CNC Shield;
- drivers A4988;
- motores a pasos;
- sensores Hall digitales como límites;
- GRBL como firmware.

La calibración de pasos/mm se hace con comandos de GRBL:

```text
$100=...
$101=...
```

El homing se activa con:

```text
$22=1
```

Los límites duros pueden dejarse apagados durante pruebas:

```text
$21=0
```

## Comandos Principales

Generar dibujo:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate

python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --landscape-bands 4 \
  --internal-lines 3 \
  --max-contours 4
```

Ejecutar dibujo con homing:

```bash
cd ~/Documents/GitHub/contraespacios/Filmic
source .venv/bin/activate

python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --port /dev/ttyACM0 \
  --homing \
  --calibrate-area \
  --set-work-zero \
  --unlock
```

El comando anterior mide el área útil antes de dibujar. Si quieres ejecutar usando un área manual sin calibrar, puedes usar:

```bash
python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --port /dev/ttyACM0 \
  --homing \
  --set-work-zero \
  --unlock \
  --work-width-mm 30 \
  --work-height-mm 32
```

Ejecutar dibujo sin homing, solo para diagnóstico:

```bash
python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --port /dev/ttyACM0 \
  --no-homing \
  --set-work-zero \
  --unlock
```

## Git

Los datos de sesión no deben vivir en el repositorio. Mantén:

```text
/home/pi/data
```

separado del código. Así `git pull` puede actualizar scripts y documentación sin tocar fotos, JSON de sesión, previews o G-code generados.
