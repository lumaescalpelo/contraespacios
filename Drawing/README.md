# Contra Espacios · Drawing

Motor de generación de dibujo SVG para sesiones de **Contra Espacios**.

Este módulo lee fotos y lecturas ambientales guardadas por Node-RED en:

```text
/home/pi/data/sessions/Sxx/
```

y genera:

```text
/home/pi/data/sessions/Sxx/output/drawing.svg
/home/pi/data/sessions/Sxx/output/preview.png
/home/pi/data/sessions/Sxx/output/metadata.json
/home/pi/data/sessions/Sxx/output/generation_log.json
```

La salida SVG usa coordenadas físicas en milímetros. Por defecto trabaja en un área de:

```text
16 mm x 43 mm
```

También puede usarse:

```text
32 mm x 43 mm
```

cambiando argumentos del script. No se controla desde OLED porque es una decisión técnica/configurable, no una acción de operación diaria.

---

## 1. Instalación en Raspberry Pi 3B+

Entrar a la carpeta:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
```

Instalar dependencias del sistema:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-numpy python3-pil
```

Crear entorno virtual con acceso a paquetes del sistema:

```bash
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

Instalar dependencias Python:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

La dependencia instalada por `pip` es mínima:

```text
svgwrite
```

OpenCV, NumPy y Pillow se instalan por `apt`, que suele ser más estable en Raspberry Pi que compilar media civilización desde `pip`.

---

## 2. Estructura esperada de sesión

Ejemplo:

```text
/home/pi/data/sessions/S01/
├── session.json
├── photos/
│   ├── photo_001_20260621T053000Z.jpg
│   └── photo_002_20260621T053200Z.jpg
├── environment/
│   ├── env_001_20260621T053100Z.json
│   └── env_002_20260621T053300Z.json
└── output/
```

Las fotos deben ser JPEG válidos.

Las lecturas ambientales deben contener:

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

Si una lectura tiene `null` o no está completa, no se usa.

---

## 3. Ejecutar manualmente

Para generar un dibujo de `S01`:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate

python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 16 \
  --film-height-mm 43
```

Para trabajar en 32 mm x 43 mm:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 32 \
  --film-height-mm 43
```

---

## 4. Salida para Node-RED

El script imprime un JSON en stdout.

Ejemplo correcto:

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
  "photos_used": 3,
  "environment_readings_used": 3,
  "duration_seconds": 12.4
}
```

Ejemplo de error:

```json
{
  "ok": false,
  "type": "drawing_result",
  "session_id": "S01",
  "message": "La sesión S01 no tiene fotos válidas."
}
```

---

## 5. Nodo Node-RED `exec`

Configura un nodo `exec`.

Comando base:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Activar:

```text
Append msg.payload
```

El nodo Function anterior debe poner en `msg.payload` algo como:

```text
--session S01 --data-root /home/pi/data --film-width-mm 16 --film-height-mm 43
```

Hay ejemplos en:

```text
node_red_examples/
```

---

## 6. Relación con la mecánica

Este motor genera un trazo continuo porque el mecanismo no tiene eje Z para levantar marcador.

Eso significa que los saltos entre contornos se convierten en líneas reales, como en una pantalla de arena, juguete de dos perillas o Etch A Sketch.

Cuando más adelante se genere G-code, esta misma lógica ayuda porque no depende de levantar herramienta.

---

## 7. Qué hace el algoritmo v1

### Imagen

- lee todas las fotos válidas de la sesión;
- recorta al aspecto físico de la película;
- reduce resolución para no bloquear la Raspberry Pi;
- promedia fotos;
- detecta bordes;
- extrae contornos;
- simplifica puntos.

### Ambiente

- lee todas las lecturas válidas;
- calcula promedios y variaciones;
- convierte temperatura, humedad, AQI, TVOC y eCO2 en parámetros visuales;
- altera densidad, ondulación y ruido del trazo.

### Salida

- genera una trayectoria ambiental;
- agrega contornos derivados de imagen;
- une todo en un solo path continuo;
- escribe SVG y preview.

---

## 8. Archivos principales

```text
generate_drawing.py      Script principal
drawing_config.py        Configuración física y visual
session_loader.py        Carga fotos y lecturas válidas
environment_analysis.py  Convierte lecturas en parámetros visuales
image_analysis.py        Extrae contornos de fotos
svg_generator.py         Escribe dibujo SVG
preview_generator.py     Escribe preview PNG
utils.py                 Funciones auxiliares
```

---

## 9. Prueba mínima

Después de guardar al menos una foto y una lectura válida:

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate
python3 generate_drawing.py --session S01 --data-root /home/pi/data
```

Luego revisa:

```bash
ls -lh /home/pi/data/sessions/S01/output
```

Deberías ver:

```text
drawing.svg
preview.png
metadata.json
generation_log.json
```
