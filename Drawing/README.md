# Contra Espacios · Drawing v3 Landscape

Esta versión v3 está pensada específicamente para lo que describiste:

- **formato horizontal** desde el origen;
- **43 x 16 mm** como valor predeterminado;
- sin relleno total de líneas de borde a borde;
- salida más **paisaje**, más **topográfica** y más **elocuente** en formato pequeño;
- menor detalle microscópico y mayor énfasis en:
  - masas principales,
  - contornos grandes,
  - bandas parciales,
  - líneas internas sugerentes.

La idea es que la imagen siga siendo una reminiscencia de la escena, pero con un lenguaje más adecuado para un mecanismo sin eje Z.

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

## 2. Estructura esperada

```text
/home/pi/data/sessions/S01/
├── session.json
├── photos/
├── environment/
└── output/
```

---

## 3. Ejecución básica

### Formato horizontal 43 x 16 mm

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate

python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 43 \
  --film-height-mm 16
```

### Formato horizontal 43 x 32 mm

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 43 \
  --film-height-mm 32
```

---

## 4. Qué cambia visualmente respecto a v2

### v2
- raster más dominante;
- más líneas de barrido;
- sensación más mecánica.

### v3
- menos líneas horizontales completas;
- bandas parciales en zonas con masa visual;
- contornos simplificados de las masas oscuras;
- líneas internas suaves tipo relieve/paisaje;
- lectura horizontal más natural.

---

## 5. Parámetros más útiles

### Menos detalle y más limpieza

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --landscape-bands 6 \
  --internal-lines 3 \
  --max-contours 10
```

### Más detalle visual

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --landscape-bands 8 \
  --internal-lines 5 \
  --max-contours 16 \
  --quantization_levels 6
```

### Más parecido a paisaje suave

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --blur-size 9 \
  --band-amplitude-mm 0.70 \
  --internal-amplitude-mm 0.40
```

---

## 6. Salidas

```text
/home/pi/data/sessions/S01/output/drawing.svg
/home/pi/data/sessions/S01/output/preview.png
/home/pi/data/sessions/S01/output/metadata.json
/home/pi/data/sessions/S01/output/generation_log.json
```

---

## 7. Node-RED

El `exec` puede seguir funcionando igual.

Comando base:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Con `Append msg.payload` activado.

Function sugerido:

```text
--session S01 --data-root /home/pi/data --film-width-mm 43 --film-height-mm 16
```

---

## 8. Idea visual de esta versión

La meta de v3 no es rellenar toda la película, sino construir una imagen que se lea como:

- escena resumida,
- contorno/paisaje,
- bandas topográficas parciales,
- estructura principal,
- y continuidad mecánica posible.

