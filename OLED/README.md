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

## 2. Dependencias necesarias

Estas dos líneas son importantes para `gpiozero` en Raspberry Pi OS moderno:

```bash
sudo apt install -y python3-lgpio python3-gpiozero
python3 -m venv --system-site-packages .venv
```

Instalación completa recomendada desde la carpeta del módulo:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
sudo apt update
sudo apt install -y python3-lgpio python3-gpiozero python3-pil python3-smbus i2c-tools
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install pillow smbus2
```

La parte importante es `--system-site-packages`, porque permite que el entorno virtual vea `python3-lgpio` y `python3-gpiozero`.

---

## 3. Qué corrige esta versión

Esta versión conserva el método que funcionó:

```text
SH1107 con RAM completa 128x128
```

Aunque la pantalla visible sea de 128x96, el controlador puede trabajar con memoria interna de 128x128. Por eso el programa escribe las 16 páginas completas.

Cambios de esta versión:

- Se mantiene `--ram-y-offset 64`, porque el programa normal sí se mostró correctamente.
- Se agrega `left_margin = 2` por defecto para evitar que la primera letra se corte. Si `LINEA` se veía como `_INEA`, esto lo corrige.
- Se acelera un poco la escritura I2C usando bloques de 16 bytes.
- Se elimina el título del menú para que no se escondan las opciones.
- En el menú ya no aparece `CONTRA ESPACIOS`, `Menu principal` ni el renglón vacío.
- El menú muestra directamente las opciones y las instrucciones de botones.

---

## 4. Hardware conectado

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

## 5. Botones

Los botones están conectados de izquierda a derecha a partir del pin físico 11 de la Raspberry Pi.

| Posición física | Pin físico | GPIO | Función |
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

Si no aparece:

- revisar VCC,
- revisar GND,
- revisar SDA en GPIO2,
- revisar SCL en GPIO3,
- confirmar que I2C está activado,
- probar cables más cortos.

---

## 8. Probar pantalla

```bash
python3 oled-test.py --screen-test
```

Debe mostrar:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
...
```

Si todavía se corta la primera letra, aumentar el margen izquierdo:

```bash
python3 oled-test.py --screen-test --left-margin 3
```

o:

```bash
python3 oled-test.py --screen-test --left-margin 4
```

Si queda demasiado separado:

```bash
python3 oled-test.py --screen-test --left-margin 1
```

El default actual es:

```text
--left-margin 2
```

---

## 9. No mover esto si el programa normal ya se ve bien

El programa usa por defecto:

```text
--ram-y-offset 64
```

Ese valor se conserva porque fue el que mostró correctamente el programa normal.

Las pruebas con otros offsets pueden verse mal porque están explorando otras zonas de la RAM interna. No significa que haya que cambiar el valor base.

---

## 10. Menú actual

El menú ya no muestra encabezados. Ahora se ve así:

```text
> Capturar foto
  Capturar ambiente
  Generar dibujo
  Ejecutar dibujo
  Estado
  Acerca de

B1/B2 mover
B3 ok B4 atras
B5 estado
```

Esto permite que el selector y el texto inferior no queden ocultos al llegar al final de la lista.

---

## 11. Qué hace cada opción

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

## 12. Qué hace cada botón

### Botón 1 - GPIO17

Sube en el menú.

### Botón 2 - GPIO27

Baja en el menú.

### Botón 3 - GPIO22

Selecciona la opción marcada.

### Botón 4 - GPIO23

Vuelve al menú.

### Botón 5 - GPIO24

Muestra el estado.

---

## 13. Salir del programa

Presionar:

```text
Ctrl+C
```

---

## 14. Estado de esta prueba

- [x] OLED en GPIO2/GPIO3.
- [x] Botones en GPIO17, GPIO27, GPIO22, GPIO23, GPIO24.
- [x] Mapeo de botones de izquierda a derecha.
- [x] Escritura completa de RAM SH1107 128x128.
- [x] `--ram-y-offset 64` como valor funcional.
- [x] Margen izquierdo para evitar corte de texto.
- [x] Menú sin encabezado para evitar ocultar opciones.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Acciones simuladas.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
