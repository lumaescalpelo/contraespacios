# Drawing

Motor de generación de dibujo para Contra Espacios.

`Drawing` toma fotos y lecturas ambientales de una sesión, genera una interpretación gráfica, guarda archivos de diagnóstico y produce el G-code que después ejecuta GRBL.

## Qué Hace

```text
lee /home/pi/data/sessions/<SESSION_ID>/photos/
lee /home/pi/data/sessions/<SESSION_ID>/environment/
genera drawing.svg
genera preview.png
genera process_steps/
genera drawing.gcode
responde JSON para Node-RED/OLED
```

`Drawing` no mueve motores. El movimiento físico se hace después con el ejecutor GRBL/Filmic.

## Área Actual

El área de trabajo actual es:

```text
30 mm x 32 mm
```

Por defecto:

```text
ancho X: 30 mm
alto Y: 32 mm
```

Si se necesita indicarlo explícitamente:

```text
--film-width-mm 30 --film-height-mm 32
```

## Convención De Coordenadas

La máquina quedó configurada para hacer homing en:

```text
esquina superior izquierda
```

La convención física esperada es:

```text
X positivo: derecha
Y positivo: abajo
```

Para la máquina actual, donde `+Y` baja físicamente, esta versión genera `drawing.gcode` con:

```text
--gcode-y-mode direct
--path-start-corner top_right
```

Ese modo manda Y sin transformar al escribir el G-code:

```text
Y_gcode = Y_dibujo
```

Si en una prueba futura necesitas invertir Y:

```text
--gcode-y-mode flip
```

## Configuración GRBL Usada En Pruebas

Valores comprobados hasta este punto:

```text
$100=44.440
$101=44.440
$27=10.000
$21=0
$22=1
$23=1
$3=0
```

Significado:

```text
$100/$101 -> pasos por mm de X/Y, igualados para pruebas
$27       -> retirada después de tocar sensores de homing
$21=0     -> límites duros apagados durante pruebas
$22=1     -> homing activado
$23=1     -> homing hacia esquina superior izquierda en esta máquina
$3=0      -> dirección normal de movimiento
```

Antes de dibujar físicamente, confirmar en bCNC:

```text
$H
?
```

El estado debe quedar en `Idle` y sin `Pn:X` ni `Pn:Y`.

## Instalar

En Raspberry Pi:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing

sudo apt update
sudo apt install -y \
  python3-venv \
  python3-pip \
  python3-opencv \
  python3-numpy \
  python3-pil

rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt`:

```text
svgwrite
pyserial
```

OpenCV, NumPy y Pillow se instalan con `apt` para evitar compilaciones innecesarias en Raspberry Pi.

## Estructura De Datos

La sesión debe existir en:

```text
/home/pi/data/sessions/<SESSION_ID>/
```

Ejemplo:

```text
/home/pi/data/sessions/S01/
├── photos/
│   ├── photo_001.jpg
│   └── photo_002.jpg
├── environment/
│   ├── env_001.json
│   └── env_002.json
└── output/
```

Lectura ambiental válida:

```json
{
  "ok": true,
  "aht_ok": true,
  "ens_ok": true,
  "temperature": 26.5,
  "humidity": 47.0,
  "aqi": 1,
  "tvoc": 21,
  "eco2": 400
}
```

## Generar Dibujo

Comando recomendado:

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

Ese comando usa por defecto:

```text
--film-width-mm 30
--film-height-mm 32
--gcode-y-mode direct
--path-start-corner top_right
```

Comando equivalente explícito:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 30 \
  --film-height-mm 32 \
  --gcode-y-mode direct \
  --path-start-corner top_right \
  --landscape-bands 4 \
  --internal-lines 3 \
  --max-contours 4
```

## Salidas

Después de generar:

```text
/home/pi/data/sessions/<SESSION_ID>/output/
├── drawing.svg
├── drawing.gcode
├── preview.png
├── metadata.json
├── generation_log.json
└── process_steps/
```

`drawing.gcode`:

```text
usa milímetros
usa coordenadas absolutas
no manda $H
no configura GRBL
requiere homing antes de ejecutarse
```

## process_steps

La carpeta:

```text
/home/pi/data/sessions/<SESSION_ID>/output/process_steps/
```

contiene:

```text
00_manifest.json
01_source_photos_contact_sheet.png
02_session_summary.json
03_environment_summary.json
04_composite_gray.png
05_smoothed.png
06_quantized.png
07_contours_overlay.png
08_landscape_bands_preview.png
09_internal_lines_preview.png
10_contour_paths_preview.png
11_final_ordered_paths_preview.png
12_path_groups_metadata.json
README_steps.txt
```

Sirve para revisar cómo se transformó la imagen antes de generar SVG y G-code.

## Respuesta JSON

Al terminar, el script imprime un JSON:

```json
{
  "ok": true,
  "type": "drawing_result",
  "session_id": "S01",
  "message": "Dibujo generado",
  "svg": "/home/pi/data/sessions/S01/output/drawing.svg",
  "preview": "/home/pi/data/sessions/S01/output/preview.png",
  "gcode": "/home/pi/data/sessions/S01/output/drawing.gcode",
  "gcode_done": true,
  "session_has_gcode": true,
  "metadata": "/home/pi/data/sessions/S01/output/metadata.json",
  "generation_log": "/home/pi/data/sessions/S01/output/generation_log.json",
  "process_steps_dir": "/home/pi/data/sessions/S01/output/process_steps"
}
```

Node-RED usa esos campos para actualizar la OLED:

```text
Dib: OK
G: OK
```

## Probar Sintaxis

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate

python3 -m py_compile *.py
```

Si no imprime nada, la sintaxis está bien.

## Integración Con Node-RED

Nodo `exec`:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Activar:

```text
Append msg.payload
```

Payload típico:

```text
--session S01 --data-root /home/pi/data --landscape-bands 4 --internal-lines 3 --max-contours 4
```

Si se quiere dejar explícita la orientación y el arranque:

```text
--session S01 --data-root /home/pi/data --gcode-y-mode direct --path-start-corner top_right --landscape-bands 4 --internal-lines 3 --max-contours 4
```

## Ejecutar El G-code

El G-code generado se ejecuta después desde el módulo de ejecución GRBL/Filmic.

Secuencia esperada:

```text
homing $H
poner cero de trabajo G10 L20 P1 X0 Y0
transmitir drawing.gcode
reportar progreso a Node-RED/OLED
```

No uses `Drawing` para corregir alarmas de GRBL. Si aparece `ALARM`, primero revisar sensores, homing, `$27`, `$23`, `$100` y `$101`.

## Git

Esta carpeta incluye `.gitignore` para evitar subir:

```text
.venv/
__pycache__/
drawing.svg
drawing.gcode
preview.png
metadata.json
generation_log.json
process_steps/
```
