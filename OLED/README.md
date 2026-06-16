# Contra Espacios - OLED y botones

Programa de prueba para la pantalla OLED I2C y cinco botones físicos del proyecto **Contra Espacios**.

Este programa se llama:

```text
oled-test.py
```

La ruta esperada dentro del repositorio es:

```text
~/Documents/GitHub/contraespacios/OLED/oled-test.py
```

---

## 1. Qué corrige esta versión

Esta versión corrige dos problemas:

1. **GPIO en Raspberry Pi OS Trixie**  
   Se fuerza el uso de `LGPIOFactory` para que `gpiozero` no caiga al backend experimental `NativeFactory`.

2. **Pantalla con ruido o texto roto**  
   Se usa por defecto el driver `sh1107` con tamaño `128x96`, porque esta pantalla OLED requiere controlarse así. Si se controla como `ssd1306`, puede mostrar ruido, texto cortado o comportamiento inestable. Porque aparentemente hasta una pantalla de 1 pulgada tiene una crisis de identidad.

También se corrigió otra cosa importante:

3. **Los botones ya no escriben directo a la pantalla desde callbacks**  
   Los callbacks de `gpiozero` corren en hilos. Antes, al presionar un botón, el callback intentaba escribir directo al bus I2C y eso podía provocar errores como:

```text
OSError: [Errno 5] Input/output error
DeviceNotFoundError: I2C device not found on address: 0x3C
```

Ahora los botones solo mandan eventos a una cola. El loop principal lee esa cola y actualiza la OLED. Más aburrido, más estable. Qué tragedia.

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

Todas estas instrucciones parten desde `Home`.

### 5.1 Entrar a la carpeta del programa

```bash
cd ~/Documents/GitHub/contraespacios/OLED
```

### 5.2 Instalar paquetes del sistema

```bash
sudo apt update
sudo apt install -y python3-lgpio python3-gpiozero python3-pil i2c-tools
```

### 5.3 Crear entorno virtual con paquetes del sistema

Es importante usar `--system-site-packages` para que el entorno virtual vea `python3-lgpio`.

```bash
cd ~/Documents/GitHub/contraespacios/OLED
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

### 5.4 Instalar librería OLED

```bash
pip install luma.oled
```

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

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-test.py
```

---

## 9. Ejecutar en consola sin OLED

Esto sirve para probar botones aunque la pantalla esté fallando:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-test.py --display console
```

---

## 10. Probar otros drivers de pantalla

La pantalla debería funcionar con:

```bash
python3 oled-test.py --display sh1107
```

Si se necesita probar:

```bash
python3 oled-test.py --display sh1106
```

o:

```bash
python3 oled-test.py --display ssd1306
```

Para tu pantalla, la opción recomendada es:

```bash
python3 oled-test.py --display sh1107
```

---

## 11. Rotar pantalla

Si el texto aparece girado:

```bash
python3 oled-test.py --rotate 1
```

Opciones:

```text
0
1
2
3
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
- [x] Driver SH1107 128x96 por defecto.
- [x] Uso de LGPIOFactory.
- [x] Cola de eventos para no escribir OLED desde callbacks.
- [x] Menú de prueba.
- [x] Acciones simuladas.
- [ ] Integrar captura real de ESP32CAM.
- [ ] Integrar lectura real de ENS160 + AHT2X.
- [ ] Integrar generación real de SVG/G-code.
- [ ] Integrar envío real a GRBL.
