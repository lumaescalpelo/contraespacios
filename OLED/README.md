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

## 2. Qué cambia esta versión

Esta versión deja de probar drivers genéricos y se concentra en el problema real observado:

- con `sh1107-direct --multiplex 0x7F`, la pantalla escribe arriba pero en orden raro;
- aparecen líneas 9 y 10 arriba;
- luego hay espacios;
- luego aparecen líneas 4 a 7;
- con `--display-offset 32`, aparecen líneas 8, 9 y 10 arriba.

Eso indica que el problema probablemente sí está en cómo se está escribiendo la memoria de la pantalla.

El SH1107 puede tener una memoria interna de:

```text
128 x 128
```

aunque el panel visible sea:

```text
128 x 96
```

La versión anterior escribía principalmente una imagen de 128x96 sobre 12 páginas. Esta versión crea una imagen interna de:

```text
128 x 128
```

y escribe las 16 páginas completas de RAM.

Luego coloca el contenido visible 128x96 dentro de esa RAM usando:

```text
--ram-y-offset
```

Esto permite encontrar en qué zona de la RAM interna está la ventana visible del panel.

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

## 5. Dependencias necesarias

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
pip install pillow smbus2
```

---

## 6. Activar I2C

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

## 7. Confirmar que la pantalla aparece

```bash
i2cdetect -y 1
```

Debe aparecer algo como:

```text
3c
```

---

## 8. Primera prueba recomendada

```bash
python3 oled-test.py --screen-test
```

Esta prueba usa por defecto:

```text
--ram-y-offset 64
```

Debe buscar que aparezca:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
...
```

desde la parte superior.

---

## 9. Probar posiciones verticales dentro de la RAM

Probar en este orden:

```bash
python3 oled-test.py --screen-test --ram-y-offset 64
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 32
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 0
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 96
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 16
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 48
```

```bash
python3 oled-test.py --screen-test --ram-y-offset 80
```

El valor correcto es el que muestra la línea 1 arriba y las líneas siguientes en orden.

---

## 10. Calibración vertical

Para ver marcas cada 8 pixeles:

```bash
python3 oled-test.py --calibrate-y
```

También se puede combinar con offsets:

```bash
python3 oled-test.py --calibrate-y --ram-y-offset 64
```

```bash
python3 oled-test.py --calibrate-y --ram-y-offset 32
```

Esto ayuda a identificar qué zona de la RAM está apareciendo físicamente en la pantalla.

---

## 11. Ajustes adicionales

### Display offset

```bash
python3 oled-test.py --screen-test --display-offset 32
```

### Start line

```bash
python3 oled-test.py --screen-test --start-line 32
```

### Segment remap y COM scan

```bash
python3 oled-test.py --screen-test --segment-remap 0xA0 --com-scan 0xC0
```

```bash
python3 oled-test.py --screen-test --segment-remap 0xA1 --com-scan 0xC8
```

### Columna

Si el primer pixel sigue cortado:

```bash
python3 oled-test.py --screen-test --column-offset 1
```

```bash
python3 oled-test.py --screen-test --column-offset 2
```

---

## 12. Ejecutar menú normal

Cuando encuentres un `ram-y-offset` correcto:

```bash
python3 oled-test.py --ram-y-offset 64
```

Cambiando `64` por el valor que haya funcionado.

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
- [x] Escritura completa de RAM SH1107 128x128.
- [x] `--ram-y-offset` para ubicar la ventana visible.
- [x] Calibración vertical.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Encontrar offset correcto para esta OLED.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
