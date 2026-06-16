# Contra Espacios - OLED y botones

Programa de prueba para la pantalla OLED I2C y cinco botones físicos del proyecto **Contra Espacios**.

Archivo principal:

```text
oled-test.py
```

Ruta esperada:

```text
~/Documents/GitHub/contraespacios/OLED/oled-test.py
```

---

## 1. Forma normal de ejecución

Entrar al directorio del módulo:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
```

Activar entorno:

```bash
source .venv/bin/activate
```

Ejecutar:

```bash
python3 oled-test.py
```

---

## 2. Por qué esta versión prueba otros modelos

La prueba anterior ya demostró que los botones funcionan, pero la OLED no está mapeando bien la memoria de pantalla.

Síntomas observados:

- En `screen-test` solo aparecen las líneas 8, 9 y 10 abajo.
- El primer pixel de la palabra `LINEA` aparece cortado.
- Hay líneas basura al final de la pantalla, hacia la derecha.
- Los offsets no corrigen lo suficiente.

Eso indica que no conviene seguir empujando offsets a ciegas. Es mejor probar otro modelo/controlador de pantalla.

Esta versión permite probar:

```text
ssd1306
sh1106
sh1107
ssd1306-direct
sh1106-direct
sh1107-direct
```

El nuevo default es:

```text
ssd1306
```

porque el síntoma actual sugiere que el mapeo SH1107 directo no corresponde a tu módulo.

---

## 3. Hardware conectado

### OLED I2C

| OLED | Raspberry Pi |
|---|---|
| SDA | GPIO2 |
| SCL | GPIO3 |
| VCC | 3.3V o 5V según módulo |
| GND | GND |

Dirección esperada:

```text
0x3C
```

---

## 4. Botones

Los botones están conectados de izquierda a derecha a partir del pin físico 11 de la Raspberry Pi.

| Posición física | Pin físico | GPIO | Función en menú |
|---|---:|---:|---|
| Botón 1 | 11 | GPIO17 | Arriba / anterior |
| Botón 2 | 13 | GPIO27 | Abajo / siguiente |
| Botón 3 | 15 | GPIO22 | Seleccionar |
| Botón 4 | 16 | GPIO23 | Volver al menú |
| Botón 5 | 18 | GPIO24 | Ver estado |

Cableado esperado:

```text
GPIO ---- botón ---- GND
```

El programa usa resistencias internas pull-up:

```python
pull_up=True
```

---

## 5. Qué hace cada botón

### Botón 1 - GPIO17 - Arriba

Mueve el cursor del menú hacia arriba.

Si estás en otra pantalla, regresa al menú.

### Botón 2 - GPIO27 - Abajo

Mueve el cursor del menú hacia abajo.

Si estás en otra pantalla, regresa al menú.

### Botón 3 - GPIO22 - Seleccionar

Ejecuta la opción marcada en el menú.

Opciones actuales:

```text
Capturar foto
Capturar ambiente
Generar dibujo
Ejecutar dibujo
Estado
Acerca de
```

Todas las acciones son simuladas.

### Botón 4 - GPIO23 - Volver

Regresa al menú principal.

### Botón 5 - GPIO24 - Estado

Muestra el estado interno del sistema.

---

## 6. Dependencias necesarias

Estas líneas son importantes para `gpiozero` en Raspberry Pi OS moderno:

```bash
sudo apt install -y python3-lgpio python3-gpiozero
python3 -m venv --system-site-packages .venv
```

Instalación completa recomendada:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
sudo apt update
sudo apt install -y python3-lgpio python3-gpiozero python3-pil python3-smbus i2c-tools
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install luma.oled pillow smbus2
```

---

## 7. Activar I2C

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

---

## 8. Confirmar que la pantalla aparece

```bash
i2cdetect -y 1
```

Debe aparecer algo como:

```text
3c
```

Si no aparece:

- revisar VCC,
- revisar GND,
- revisar SDA en GPIO2,
- revisar SCL en GPIO3,
- confirmar que I2C está activado,
- probar cables más cortos.

---

## 9. Prueba rápida con driver default

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-test.py --screen-test
```

El default ahora usa:

```text
--driver ssd1306
```

---

## 10. Probar modelos de pantalla

Ejecutar uno por uno:

```bash
python3 oled-test.py --screen-test --driver ssd1306
```

```bash
python3 oled-test.py --screen-test --driver sh1106
```

```bash
python3 oled-test.py --screen-test --driver sh1107
```

Si esos no quedan bien, probar los drivers directos:

```bash
python3 oled-test.py --screen-test --driver ssd1306-direct
```

```bash
python3 oled-test.py --screen-test --driver sh1106-direct
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct
```

La pantalla correcta es la que muestre:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
...
```

desde la parte superior, sin basura al lado derecho.

---

## 11. Ajustes útiles

### Rotación con luma

```bash
python3 oled-test.py --screen-test --driver ssd1306 --rotate 1
```

Opciones:

```text
0
1
2
3
```

### Ancho y alto

Si 128x96 no funciona bien, probar 128x64 solo como diagnóstico:

```bash
python3 oled-test.py --screen-test --driver ssd1306 --height 64
```

### Offset de columna en drivers directos

```bash
python3 oled-test.py --screen-test --driver sh1106-direct --column-offset 2
```

```bash
python3 oled-test.py --screen-test --driver sh1106-direct --column-offset 4
```

### Multiplex en drivers directos

```bash
python3 oled-test.py --screen-test --driver ssd1306-direct --multiplex 0x5F
```

```bash
python3 oled-test.py --screen-test --driver ssd1306-direct --multiplex 0x7F
```

---

## 12. Ejecutar menú normal cuando encuentres el driver correcto

Ejemplo:

```bash
python3 oled-test.py --driver ssd1306
```

o:

```bash
python3 oled-test.py --driver sh1106
```

---

## 13. Menú actual

### Capturar foto

Simula captura de foto.

### Capturar ambiente

Simula lectura ambiental.

### Generar dibujo

Simula generación de SVG y G-code. Requiere foto y ambiente simulados.

### Ejecutar dibujo

Simula ejecución del dibujo. Requiere G-code simulado.

### Estado

Muestra el estado de todos los pasos.

### Acerca de

Muestra una descripción breve del proyecto.

---

## 14. Salir del programa

Presionar:

```text
Ctrl+C
```

---

## 15. Estado de esta prueba

- [x] OLED en GPIO2/GPIO3.
- [x] Botones en GPIO17, GPIO27, GPIO22, GPIO23, GPIO24.
- [x] Mapeo de botones de izquierda a derecha.
- [x] Prueba de varios modelos de pantalla.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Identificar driver exacto de la OLED.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
