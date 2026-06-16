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

Esta vuelve a ser la forma normal. Nada de rutas kilométricas desde Home, porque eso fue una idea técnicamente válida y humanamente fastidiosa. El progreso a veces consiste en deshacer lo innecesario.

---

## 2. Qué corrige esta versión

Esta versión cambia tres cosas importantes:

1. **Quita el modo consola como fallback.**  
   Si falla la OLED, el programa intenta reconectarse a la pantalla. Ya no cambia silenciosamente a consola.

2. **Mueve el texto hacia arriba.**  
   El texto se dibuja desde `y = 0`, con `page_offset = 0` por defecto.

3. **Limpia la memoria completa de la pantalla antes de redibujar.**  
   Esto reduce basura visual o texto viejo que queda debajo cuando se navega en el menú.

También mantiene:

- driver directo **SH1107 128x96**,
- `LGPIOFactory`,
- cola de eventos para botones,
- escritura OLED solo desde el loop principal.

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

Muestra el estado interno del sistema:

```text
Foto
Ambiente
SVG
G-code
Dibujo
```

---

## 6. Dependencias necesarias

Estas dos líneas son importantes y deben quedar documentadas porque resuelven el problema de `gpiozero` en Raspberry Pi OS moderno:

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

Nota: `gpiozero`, `lgpio` y `PIL` pueden venir desde los paquetes del sistema gracias a:

```bash
python3 -m venv --system-site-packages .venv
```

Sí, esta línea importa. No es decoración ceremonial de terminal.

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

## 9. Ejecutar programa

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-test.py
```

---

## 10. Probar pantalla de alineación

```bash
python3 oled-test.py --screen-test
```

Debe verse:

```text
LINEA 1 ARRIBA
LINEA 2
LINEA 3
...
```

La línea 1 debe salir arriba.

---

## 11. Ajustes si el texto sigue cortado

Si la parte de arriba sigue cortada:

```bash
python3 oled-test.py --screen-test --page-offset 1
```

```bash
python3 oled-test.py --screen-test --page-offset 2
```

Si vuelve a verse al centro, regresar a:

```bash
python3 oled-test.py --screen-test --page-offset 0
```

Si está corrida a los lados:

```bash
python3 oled-test.py --screen-test --column-offset 2
```

```bash
python3 oled-test.py --screen-test --column-offset 4
```

Si necesita un margen pequeño arriba:

```bash
python3 oled-test.py --screen-test --top-margin 2
```

Si está invertida:

```bash
python3 oled-test.py --rotate-180
```

---

## 12. Qué debe mostrar

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

## 13. Menú actual

### Capturar foto

Simula captura de foto.

Marca:

```text
Foto: OK
```

Más adelante llamará al programa real de ESP32CAM.

### Capturar ambiente

Simula lectura ambiental.

Marca:

```text
Ambiente: OK
```

Más adelante llamará al programa real del ENS160 + AHT2X conectado directo a Raspberry Pi.

### Generar dibujo

Simula generación de SVG y G-code.

Solo funciona si antes están listas:

- foto,
- ambiente.

Si falta algo, indica:

```text
Falta foto/amb
```

### Ejecutar dibujo

Simula ejecución del dibujo.

Solo funciona si antes existe G-code.

Si falta, indica:

```text
Falta Gcode
```

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
- [x] Driver directo SH1107 128x96.
- [x] `page_offset=0` por defecto.
- [x] Reconexión OLED si falla I2C.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
