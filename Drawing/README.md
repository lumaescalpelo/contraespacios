# Drawing

Motor de generación de dibujo para Contra Espacios.

`Drawing` hace:

```text
leer fotos y lecturas ambientales
generar drawing.svg
generar preview.png
generar process_steps/
generar drawing.gcode
responder JSON para Node-RED/OLED
```

`Drawing` no se conecta con GRBL y no mueve motores. La ejecución física la hace `Filmic`.

## Área Actual

```text
30 mm x 32 mm
```

Los valores por defecto están en:

```text
drawing_config.py
generate_drawing.py
```

Si hace falta pasarlos explícitamente:

```text
--film-width-mm 30 --film-height-mm 32
```

## Instalar

```bash
cd ~/Documents/GitHub/contraespacios/Drawing

sudo apt update
sudo apt install -y \
  python3-venv \
  python3-pip \
  python3-opencv \
  python3-numpy \
  python3-pil

python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt`:

```text
svgwrite
```

## Entrada De Datos

El script lee sesiones desde:

```text
/home/pi/data/sessions/<SESSION_ID>/
```

Ejemplo:

```text
/home/pi/data/sessions/S01/
├── photos/
├── environment/
└── output/
```

Las fotos deben ser JPEG válidos dentro de `photos/`.

Las lecturas ambientales deben ser JSON válidos dentro de `environment/`, por ejemplo:

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

## Salidas

```text
/home/pi/data/sessions/<SESSION_ID>/output/
├── drawing.svg
├── drawing.gcode
├── preview.png
├── metadata.json
├── generation_log.json
└── process_steps/
```

`drawing.gcode` usa milímetros y coordenadas absolutas. No incluye `$H`. El homing lo hace `Filmic` antes de transmitir el archivo.

## process_steps

La carpeta:

```text
/home/pi/data/sessions/<SESSION_ID>/output/process_steps/
```

incluye imágenes y JSON secuenciales para entender cómo se transformó la foto:

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

## Respuesta JSON

Al terminar imprime algo como:

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

Node-RED usa esa respuesta para actualizar:

```text
Dib: OK
G: OK
F: número de fotos
A: número de lecturas ambientales
```

## Node-RED

Nodo `exec`:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Activar:

```text
Append msg.payload
```

Argumentos típicos:

```text
--session S01 --data-root /home/pi/data --landscape-bands 4 --internal-lines 3 --max-contours 4
```

Ejemplos:

```text
node_red_examples/preparar_generate_drawing.js
node_red_examples/procesar_resultado_drawing.js
```

## Git

Esta carpeta ignora:

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