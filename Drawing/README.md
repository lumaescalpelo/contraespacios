# Contra Espacios · Drawing v4 con pasos de proceso

Esta versión genera el dibujo SVG y además guarda una carpeta con los pasos intermedios del proceso para poder entender cómo se transforma la imagen.

La corrección importante de esta versión es que `process_steps.py` ya no tiene el error de sintaxis en la escritura de `README_steps.txt`. Sí, un salto de línea mal escapado tumbó todo el motor, porque Python también tiene sus berrinches miniatura.

---

## 0. Comando rápido de instalación limpia

Ejecuta esto dentro de la Raspberry:

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

El archivo `requirements.txt` solo debe contener:

```text
svgwrite
```

OpenCV, NumPy y Pillow se instalan con `apt`, porque en Raspberry Pi eso suele ser más estable que pedirle a `pip` que compile medio planeta.

---

## 1. Estructura esperada

El script lee una sesión guardada en:

```text
/home/pi/data/sessions/S01/
```

La sesión debe tener:

```text
/home/pi/data/sessions/S01/
├── photos/
│   ├── photo_001_....jpg
│   └── photo_002_....jpg
├── environment/
│   ├── env_001_....json
│   └── env_002_....json
└── output/
```

Las fotos deben ser JPEG válidos.

Las lecturas ambientales deben ser válidas y completas, por ejemplo:

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

Si una lectura tiene `null`, no debería llegar hasta este motor. Node-RED ya está filtrando esas porquerías con admirable severidad.

---

## 2. Comando recomendado para probar

Este es el preset base que te recomiendo para revisar la versión diagnóstica:

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

Si quieres un resultado más limpio:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --landscape-bands 3 \
  --internal-lines 2 \
  --max-contours 3
```

Si quieres un resultado con más información:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --landscape-bands 5 \
  --internal-lines 4 \
  --max-contours 5
```

---

## 3. Salidas generadas

Después de correr el script, revisa:

```bash
ls -lh /home/pi/data/sessions/S01/output/
```

Deberías ver:

```text
drawing.svg
preview.png
metadata.json
generation_log.json
process_steps/
```

---

## 4. Carpeta `process_steps`

La carpeta de diagnóstico queda en:

```text
/home/pi/data/sessions/S01/output/process_steps/
```

Contiene:

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

### Qué significa cada archivo

| Archivo | Qué muestra |
|---|---|
| `01_source_photos_contact_sheet.png` | Hoja de contacto con las fotos usadas |
| `02_session_summary.json` | Resumen de fotos y lecturas usadas |
| `03_environment_summary.json` | Promedios ambientales y parámetros visuales derivados |
| `04_composite_gray.png` | Composición en gris hecha con las fotos |
| `05_smoothed.png` | Imagen suavizada antes de simplificar formas |
| `06_quantized.png` | Imagen reducida a pocos niveles tonales |
| `07_contours_overlay.png` | Contornos detectados sobre la imagen |
| `08_landscape_bands_preview.png` | Solo las bandas de paisaje |
| `09_internal_lines_preview.png` | Solo las líneas internas |
| `10_contour_paths_preview.png` | Solo trayectorias de contorno |
| `11_final_ordered_paths_preview.png` | Recorrido final continuo |
| `12_path_groups_metadata.json` | Conteos y metadatos de las trayectorias |

---

## 5. Ver resultados desde terminal

Para listar los pasos:

```bash
ls -lh /home/pi/data/sessions/S01/output/process_steps/
```

Para abrir la carpeta desde escritorio:

```bash
xdg-open /home/pi/data/sessions/S01/output/process_steps/
```

Para ver el preview final:

```bash
xdg-open /home/pi/data/sessions/S01/output/preview.png
```

Para ver el SVG:

```bash
xdg-open /home/pi/data/sessions/S01/output/drawing.svg
```

---

## 6. Cómo saber si corrió bien

La terminal debe imprimir un JSON parecido a:

```json
{
  "ok": true,
  "type": "drawing_result",
  "session_id": "S01",
  "message": "Dibujo generado",
  "svg": "/home/pi/data/sessions/S01/output/drawing.svg",
  "preview": "/home/pi/data/sessions/S01/output/preview.png",
  "metadata": "/home/pi/data/sessions/S01/output/metadata.json",
  "generation_log": "/home/pi/data/sessions/S01/output/generation_log.json",
  "process_steps_dir": "/home/pi/data/sessions/S01/output/process_steps",
  "process_manifest": "/home/pi/data/sessions/S01/output/process_steps/00_manifest.json"
}
```

Si `ok` es `true`, el dibujo y los pasos están listos.

---

## 7. Si vuelve a fallar

Primero revisa sintaxis:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate
python3 -m py_compile *.py
```

Si eso no imprime nada, la sintaxis está bien.

Luego corre:

```bash
python3 generate_drawing.py --session S01 --data-root /home/pi/data
```

Si falla, copia el error completo. Sí, completo. Los errores recortados son como mapas sin norte, muy poéticos y absolutamente inútiles.

---

## 8. Integración con Node-RED

El nodo `exec` puede seguir usando:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Con `Append msg.payload` activado.

El Function anterior puede mandar:

```text
--session S01 --data-root /home/pi/data --landscape-bands 4 --internal-lines 3 --max-contours 4
```

El JSON de salida ahora también incluye:

```json
{
  "process_steps_dir": "/home/pi/data/sessions/S01/output/process_steps",
  "process_manifest": "/home/pi/data/sessions/S01/output/process_steps/00_manifest.json"
}
```
