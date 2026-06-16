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

## 2. Error corregido

Si al probar `ssd1306` o `sh1106` aparece:

```text
DeviceDisplayModeError: Unsupported display mode: 128 x 96
```

no significa que el programa esté roto. Significa que `luma.oled` no acepta `128x96` para esos drivers.

En `luma.oled`:

- `ssd1306` no soporta `128x96`.
- `sh1106` no soporta `128x96`.
- `sh1107` sí es el candidato para `128x96`.

Por eso el default vuelve a ser:

```text
--driver sh1107
```

Para probar `ssd1306` o `sh1106`, hay que hacerlo como diagnóstico usando `--height 64`.

Sí, el ecosistema OLED decidió que el mismo conector I2C podía esconder varios controladores distintos. Una fiesta, si tu concepto de fiesta incluye tracebacks.

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
pip install luma.oled pillow smbus2
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

## 8. Prueba principal recomendada

Primero probar:

```bash
python3 oled-test.py --screen-test --driver sh1107
```

Si eso muestra correctamente:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
...
```

entonces ejecutar menú normal:

```bash
python3 oled-test.py --driver sh1107
```

---

## 9. Pruebas diagnósticas con 128x64

Estas pruebas no usan toda la pantalla. Sirven para saber si el módulo se comporta como `ssd1306` o `sh1106`.

```bash
python3 oled-test.py --screen-test --driver ssd1306 --height 64
```

```bash
python3 oled-test.py --screen-test --driver sh1106 --height 64
```

Si una de estas se ve limpia, pero solo usa una parte de la pantalla, ya sabemos más sobre el controlador real.

---

## 10. Pruebas con drivers directos

Si `sh1107` no funciona bien, probar:

```bash
python3 oled-test.py --screen-test --driver ssd1306-direct
```

```bash
python3 oled-test.py --screen-test --driver sh1106-direct
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct
```

---

## 11. Pruebas de orientación y memoria

Para drivers directos:

```bash
python3 oled-test.py --screen-test --driver sh1107-direct --page-offset 0
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct --page-offset 4
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct --multiplex 0x7F
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct --start-line 32
```

```bash
python3 oled-test.py --screen-test --driver sh1107-direct --display-offset 32
```

Para rotación con `luma`:

```bash
python3 oled-test.py --screen-test --driver sh1107 --rotate 1
```

Opciones:

```text
0
1
2
3
```

---

## 12. Cómo identificar el driver correcto

La pantalla correcta debe mostrar:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
LINEA 4
LINEA 5
...
```

desde la parte superior, sin basura a la derecha.

Si solo se ven líneas 8, 9 y 10 abajo, ese driver no sirve para este módulo.

Si aparece error `Unsupported display mode: 128 x 96`, ese driver no soporta esa resolución con `luma.oled`.

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
- [x] Corrección del error `Unsupported display mode: 128 x 96`.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Identificar driver exacto de la OLED.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
