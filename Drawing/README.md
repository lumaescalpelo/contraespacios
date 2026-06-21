
# Contra Espacios · Drawing v4 con pasos de proceso

Esta variante de la v4 guarda, además del SVG final, una carpeta con los **pasos secuenciales del proceso** para que puedas entender cómo se transforma la imagen.

La idea es que puedas revisar visualmente:

- las fotos fuente,
- la composición en gris,
- la imagen suavizada,
- la cuantización,
- los contornos detectados,
- las familias de trayectorias,
- y la trayectoria final ordenada.

---

## 1. Instalación

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-numpy python3-pil

rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Ejecución

Ejemplo base:

```bash
python3 generate_drawing.py   --session S01   --data-root /home/pi/data   --landscape-bands 4   --internal-lines 3   --max-contours 4
```

---

## 3. Archivos generados

Dentro de:

```text
/home/pi/data/sessions/S01/output/
```

se generan:

- `drawing.svg`
- `preview.png`
- `metadata.json`
- `generation_log.json`
- `process_steps/`

---

## 4. Carpeta process_steps

Dentro de `process_steps/` se guardan archivos secuenciales como:

- `00_manifest.json`
- `01_source_photos_contact_sheet.png`
- `02_session_summary.json`
- `03_environment_summary.json`
- `04_composite_gray.png`
- `05_smoothed.png`
- `06_quantized.png`
- `07_contours_overlay.png`
- `08_landscape_bands_preview.png`
- `09_internal_lines_preview.png`
- `10_contour_paths_preview.png`
- `11_final_ordered_paths_preview.png`
- `12_path_groups_metadata.json`
- `README_steps.txt`

Esto te permite ver claramente cómo va cambiando la imagen y cómo se construye el dibujo final.

---

## 5. Qué representa cada paso

- **01**: fotos válidas usadas en la sesión.
- **02**: resumen de entradas.
- **03**: resumen ambiental y parámetros visuales derivados.
- **04**: composición base en gris.
- **05**: imagen suavizada.
- **06**: reducción tonal / cuantización.
- **07**: contornos detectados.
- **08**: bandas de paisaje.
- **09**: líneas internas.
- **10**: trayectorias de contorno.
- **11**: orden final continuo para dibujar sin levantar marcador.
- **12**: metadatos de grupos y conteos.

---

## 6. Observación importante

Esta versión no cambia la lógica principal del dibujo final; agrega una **capa de inspección y análisis** para que puedas estudiar el proceso y decidir mejor qué parte conviene ajustar después.
