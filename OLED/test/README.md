# Contra Espacios - OLED test

Programa de prueba para la pantalla OLED I2C y cinco botones físicos.

Archivo:

```text
OLED/test/oled-test.py
```

Este programa solo prueba OLED, botones, menú y acciones simuladas. No manda UDP y no se conecta todavía con Node-RED.

---

## Ejecutar

```bash
cd ~/Documents/GitHub/contraespacios/OLED/test
source ../.venv/bin/activate
python3 oled-test.py
```

---

## Dependencias importantes

Estas dos líneas son necesarias para `gpiozero` en Raspberry Pi OS moderno:

```bash
sudo apt install -y python3-lgpio python3-gpiozero
python3 -m venv --system-site-packages .venv
```

Instalación recomendada desde `OLED`:

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

## Botones

Los botones están conectados de izquierda a derecha a partir del pin físico 11.

| Posición | Pin físico | GPIO | Función |
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

El programa usa:

```python
pull_up=True
```

---

## Pantalla OLED

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

Confirmar con:

```bash
i2cdetect -y 1
```

---

## Menú

La pantalla de menú solo muestra opciones, sin instrucciones de botones para evitar parpadeos o confusión visual.

```text
> Capturar foto
  Capturar ambiente
  Generar dibujo
  Ejecutar dibujo
  Estado
  Acerca de
```

---

## Prueba de pantalla

```bash
python3 oled-test.py --screen-test
```

Si se corta la primera letra:

```bash
python3 oled-test.py --screen-test --left-margin 3
```

El valor default es:

```text
--left-margin 2
```

---

## Estado

- [x] OLED funcional.
- [x] Botones funcionales.
- [x] Menú sin instrucciones para evitar flickering.
- [x] Acerca de ajustado para no cortar texto.
- [x] Acciones simuladas.
