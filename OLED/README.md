# Contra Espacios - Prueba OLED y botones

Este módulo prueba la pantalla OLED I2C y cinco botones físicos conectados a la Raspberry Pi.

El objetivo es tener una primera interfaz local para el proyecto **Contra Espacios**. Esta versión todavía no captura fotografías, no lee sensores, no genera SVG, no genera G-code y no mueve la máquina CNC. Solo simula los pasos para comprobar que pantalla, navegación y botones funcionan correctamente.

## Archivos

```text
oled-test.py
README.md
```

Ubicación sugerida dentro del repositorio:

```text
/OLED_Botones/
├── oled-test.py
└── README.md
```

## Hardware usado

### Pantalla OLED

| OLED | Raspberry Pi |
|---|---|
| SDA | GPIO2 |
| SCL | GPIO3 |
| VCC | 3.3V o 5V según módulo |
| GND | GND |

Dirección I2C esperada:

```text
0x3C
```

### Botones

| Botón | GPIO | Función |
|---|---:|---|
| Botón 1 | GPIO17 | Arriba / anterior |
| Botón 2 | GPIO27 | Abajo / siguiente |
| Botón 3 | GPIO22 | Seleccionar |
| Botón 4 | GPIO23 | Volver |
| Botón 5 | GPIO24 | Estado / acción rápida |

## Suposición de cableado

El programa asume que cada botón conecta el GPIO a **GND** al presionarse.

Por eso se usa:

```python
pull_up=True
```

Cableado típico:

```text
GPIO ---- botón ---- GND
```

No se necesita resistencia externa si se usa la resistencia pull-up interna de la Raspberry Pi.

## Instalar dependencias

En la Raspberry Pi:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv i2c-tools
```

Con entorno virtual:

```bash
cd ~/contraespacios
python3 -m venv .venv
source .venv/bin/activate
pip install gpiozero luma.oled pillow
```

Sin entorno virtual:

```bash
pip install gpiozero luma.oled pillow
```

## Activar I2C

```bash
sudo raspi-config
```

Ruta:

```text
Interface Options -> I2C -> Enable
```

Reiniciar:

```bash
sudo reboot
```

## Confirmar pantalla OLED

```bash
i2cdetect -y 1
```

Debería aparecer:

```text
3c
```

Si no aparece, revisar VCC, GND, SDA, SCL, activación de I2C y dirección de la pantalla.

## Ejecutar

Desde la carpeta del archivo:

```bash
python3 oled-test.py
```

Para salir:

```text
Ctrl+C
```

## Qué debe mostrar

Presentación inicial:

```text
CONTRA ESPACIOS

Dibujo 16mm
Ambiente + CNC

Amaranta
Chikiframe
```

Después aparece el menú:

```text
CONTRA ESPACIOS
Menu principal

> Capturar foto
  Capturar ambiente
  Generar dibujo
  Ejecutar dibujo
```

## Funciones simuladas

### Capturar foto

Marca internamente:

```text
photo_done = True
```

Más adelante llamará al script real de captura de ESP32CAM.

### Capturar ambiente

Marca internamente:

```text
environment_done = True
```

Más adelante llamará al script real de lectura del ENS160 + AHT2X conectado directo a la Raspberry Pi.

### Generar dibujo

Necesita que antes estén completos:

- Foto.
- Ambiente.

Si todo está listo, simula:

```text
SVG y Gcode OK
```

Más adelante llamará al programa real que genera SVG y G-code.

### Ejecutar dibujo

Necesita que exista G-code simulado.

Más adelante llamará al programa real que envía G-code a GRBL.

### Estado

Muestra:

```text
Foto: OK / --
Amb: OK / --
SVG: OK / --
Gcode: OK / --
Draw: OK / --
```

## Integración futura

Este programa puede crecer de dos formas.

### Opción A: interfaz directa

El programa llama scripts reales:

```python
subprocess.run(["python3", "scripts/capture_photo.py"])
subprocess.run(["python3", "scripts/read_environment.py"])
subprocess.run(["python3", "scripts/generate_drawing.py"])
subprocess.run(["python3", "scripts/send_gcode.py"])
```

### Opción B: interfaz de estado

Node-RED controla el flujo principal y este programa solo muestra estado en OLED y lee botones.

Puede comunicarse mediante:

- Archivos JSON de estado.
- HTTP local.
- Base de datos.
- Ejecución de scripts externos.

La ruta recomendada por ahora:

```text
1. Probar OLED y botones solos.
2. Probar cada script por separado.
3. Probar cada script desde Node-RED.
4. Conectar botones y OLED al flujo real.
```

## Estado de esta prueba

- [x] OLED conectada a GPIO2/GPIO3.
- [x] Botones definidos en GPIO17, GPIO27, GPIO22, GPIO23, GPIO24.
- [x] Programa de presentación.
- [x] Menú de proyecto.
- [x] Acciones simuladas.
- [x] Estado interno.
- [ ] Integración con ESP32CAM real.
- [ ] Integración con sensor ENS160 + AHT2X real.
- [ ] Integración con generación SVG/G-code.
- [ ] Integración con GRBL.
- [ ] Integración final con Node-RED.
