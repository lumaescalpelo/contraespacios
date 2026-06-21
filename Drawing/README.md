# Contra Espacios · Drawing v2

Versión ajustada para que el dibujo se parezca **mucho más a las fotos**.

La v1 privilegiaba una respuesta demasiado abstracta. Esta v2 cambia el enfoque:

- usa **composición por mediana** de las fotos de la sesión;
- aumenta el peso de la **estructura de imagen**;
- genera una base de **escaneo tonal serpentino**;
- agrega **contornos derivados de la escena**;
- deja la influencia ambiental como **modulación ligera**, no como protagonista.

Con eso el resultado debería recordar mucho mejor la escena capturada, aunque siga siendo un dibujo lineal continuo pensado para un mecanismo **sin eje Z**.

---

## 1. Instalación en Raspberry Pi 3B+

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

## 2. Qué cambió en esta versión

### v1
- líneas atmosféricas muy marcadas;
- contornos con poca presencia relativa;
- resultado más abstracto.

### v2
- el dibujo nace de un **raster tonal** basado en la luminosidad real de la imagen;
- los bordes detectados agregan relieve y estructura;
- los contornos se agregan encima del raster;
- el ambiente modifica densidad, amplitud y grosor, pero **no destruye la semejanza**.

---

## 3. Estructura esperada de sesión

```text
/home/pi/data/sessions/S01/
├── session.json
├── photos/
├── environment/
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

---

## 4. Ejecutar manualmente

```bash
cd ~/Documents/GitHub/contraespacios/Drawing
source .venv/bin/activate

python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 16 \
  --film-height-mm 43
```

Para 32 x 43 mm:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --film-width-mm 32 \
  --film-height-mm 43
```

---

## 5. Parámetros importantes

Si quieres más detalle visual:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --base-scanlines 72 \
  --samples-per-scanline 220 \
  --canny-low 35 \
  --canny-high 110
```

Si quieres menos densidad porque el marcador se satura:

```bash
python3 generate_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --base-scanlines 42 \
  --samples-per-scanline 140
```

---

## 6. Salidas

Se generan:

```text
/home/pi/data/sessions/S01/output/drawing.svg
/home/pi/data/sessions/S01/output/preview.png
/home/pi/data/sessions/S01/output/metadata.json
/home/pi/data/sessions/S01/output/generation_log.json
```

---

## 7. Node-RED

El nodo `exec` sigue funcionando igual.

Comando base:

```text
/home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
```

Con `Append msg.payload` activado.

El Function anterior puede mandar, por ejemplo:

```text
--session S01 --data-root /home/pi/data --film-width-mm 16 --film-height-mm 43
```

---

## 8. Idea visual de v2

El resultado no debe ser ya una pila de ondas abstractas, sino algo más cercano a:

- una interpretación lineal de la escena;
- con volumen por sombreado lineal;
- con contornos reconocibles;
- y con una sola trayectoria continua apta para un sistema sin levantamiento de pluma.

