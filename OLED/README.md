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

## 1. Qué corrige esta versión

Esta versión corrige la forma de ejecución y la forma de controlar la pantalla.

### 1.1 Ejecución desde Home

El programa está pensado para ejecutarse desde `Home` usando la ruta completa:

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py
```

No depende de que estés parada dentro de la carpeta `OLED`. Por fin, una pequeña victoria contra las rutas relativas, esa plaga elegante.

### 1.2 Pantalla OLED

La pantalla se controla con un driver directo para **SH1107 128x96**.

Esto evita tratarla como una `ssd1306` genérica, que en esta pantalla puede provocar:

- ruido visual,
- texto roto,
- imagen corrida,
- errores I2C,
- comportamiento inestable.

### 1.3 Botones

Los botones ya no escriben directo a la pantalla desde callbacks de `gpiozero`.

Ahora:

```text
botón -> evento -> cola -> loop principal -> OLED
```

Esto evita que los hilos de `gpiozero` intenten escribir al bus I2C al mismo tiempo.

---

## 2. Hardware conectado

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

## 3. Botones

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

## 4. Qué hace cada botón

### Botón 1 - GPIO17 - Arriba

Mueve el cursor del menú hacia arriba.

Si estás en otra pantalla, regresa al menú.

---

### Botón 2 - GPIO27 - Abajo

Mueve el cursor del menú hacia abajo.

Si estás en otra pantalla, regresa al menú.

---

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

---

### Botón 4 - GPIO23 - Volver

Regresa al menú principal.

---

### Botón 5 - GPIO24 - Estado

Muestra el estado interno del sistema:

```text
Foto
Ambiente
SVG
G-code
Dibujo
```

---

## 5. Instalar dependencias desde Home

### 5.1 Instalar paquetes del sistema

Desde Home:

```bash
sudo apt update
sudo apt install -y python3-lgpio python3-gpiozero python3-pil python3-smbus i2c-tools
```

### 5.2 Crear entorno virtual con paquetes del sistema

Desde Home:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

### 5.3 Instalar dependencias Python

```bash
pip install pillow smbus2
```

Nota: `gpiozero`, `lgpio` y `PIL` pueden venir desde los paquetes del sistema gracias a `--system-site-packages`.

---

## 6. Activar I2C

Desde Home:

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

Desde Home:

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

## 8. Ejecutar programa desde Home

Activar entorno:

```bash
source ~/Documents/GitHub/contraespacios/OLED/.venv/bin/activate
```

Ejecutar usando ruta completa:

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py
```

Este es el comando recomendado.

---

## 9. Ejecutar en consola sin OLED

Esto sirve para probar botones aunque la pantalla esté fallando:

```bash
source ~/Documents/GitHub/contraespacios/OLED/.venv/bin/activate
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py --display console
```

---

## 10. Ajustes si la imagen aparece corrida

Si la pantalla prende pero la imagen aparece corrida, prueba offsets.

### Offset de columna

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py --column-offset 2
```

También puedes probar:

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py --column-offset 4
```

### Offset de página

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py --page-offset 1
```

### Rotar 180 grados

```bash
python3 ~/Documents/GitHub/contraespacios/OLED/oled-test.py --rotate-180
```

---

## 11. Qué debe mostrar

Al iniciar:

```text
CONTRA ESPACIOS

Dibujo 16mm
Ambiente + CNC

Amaranta
Chikiframe

OLED + botones
```

Después:

```text
CONTRA ESPACIOS
Menu principal

> Capturar foto
  Capturar ambiente
  Generar dibujo
  Ejecutar dibujo
```

---

## 12. Menú actual

### Capturar foto

Simula captura de foto.

Marca:

```text
Foto: OK
```

Más adelante llamará al programa real de ESP32CAM.

---

### Capturar ambiente

Simula lectura ambiental.

Marca:

```text
Ambiente: OK
```

Más adelante llamará al programa real del ENS160 + AHT2X conectado directo a Raspberry Pi.

---

### Generar dibujo

Simula generación de SVG y G-code.

Solo funciona si antes están listas:

- foto,
- ambiente.

Si falta algo, indica:

```text
Falta foto/amb
```

---

### Ejecutar dibujo

Simula ejecución del dibujo.

Solo funciona si antes existe G-code.

Si falta, indica:

```text
Falta Gcode
```

---

### Estado

Muestra el estado de todos los pasos.

---

### Acerca de

Muestra una descripción breve del proyecto.

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
- [x] Driver directo SH1107 128x96 por defecto.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
