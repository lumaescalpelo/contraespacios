# Cargar GRBL en Arduino Uno para Contraespacios

Este documento describe como cargar GRBL en un Arduino Uno para usarlo con un CNC Shield y drivers A4988 dentro del proyecto Contraespacios.

La version recomendada es:

```text
GRBL 1.1h
```

GRBL 1.1h funciona en placas basadas en ATmega328p, como Arduino Uno o Arduino Nano.

## 1. Material necesario

```text
Arduino Uno
Cable USB
Arduino IDE
Repositorio de GRBL
Archivo grbl-contraespacios.zip
```

Para esta etapa no es necesario conectar todavia:

```text
CNC Shield
drivers A4988
motores
fuente externa
sensores de limite
```

Primero se carga y verifica el firmware en el Arduino Uno.

## 2. Descargar GRBL desde el sitio oficial

El repositorio oficial de GRBL esta en:

```text
https://github.com/gnea/grbl
```

La version recomendada es:

```text
v1.1h
```

Se puede descargar como ZIP desde GitHub o clonar el repositorio con:

```bash
git clone https://github.com/gnea/grbl.git
```

Dentro del repositorio hay una carpeta interna llamada:

```text
grbl/
```

Esa carpeta es la biblioteca que debe usar Arduino IDE. No se debe instalar todo el repositorio como biblioteca.

## 3. Modificacion de homing para maquina X/Y

El proyecto Contraespacios usa una maquina de dibujo en X/Y, sin eje Z real para el homing inicial.

Por eso se modifica el archivo:

```text
grbl/config.h
```

Buscar:

```c
#define HOMING_CYCLE_0 (1<<Z_AXIS)
#define HOMING_CYCLE_1 ((1<<X_AXIS)|(1<<Y_AXIS))
```

Cambiar por:

```c
#define HOMING_CYCLE_0 ((1<<X_AXIS)|(1<<Y_AXIS))
// #define HOMING_CYCLE_1
```

Con esta modificacion, cuando se active homing mas adelante, GRBL buscara solamente X/Y y no intentara buscar Z.

## 4. Usar el ZIP preparado: grbl-contraespacios.zip

El archivo:

```text
grbl-contraespacios.zip
```

debe contener directamente la carpeta interna de GRBL ya modificada para Contraespacios.

La estructura esperada al descomprimirlo es:

```text
grbl/
├── config.h
├── cpu_map.h
├── grbl.h
├── motion_control.c
└── ...
```

El archivo importante a comprobar es:

```text
grbl/config.h
```

Debe tener la modificacion de homing X/Y.

## 5. Instalar GRBL manualmente en Arduino IDE

En Linux, Arduino IDE normalmente usa como carpeta de sketchbook:

```text
~/Arduino
```

Las bibliotecas agregadas manualmente van en:

```text
~/Arduino/libraries
```

Crear la carpeta si no existe:

```bash
mkdir -p ~/Arduino/libraries
```

Eliminar una version previa de GRBL, si existe:

```bash
rm -rf ~/Arduino/libraries/grbl
```

Copiar la carpeta `grbl/` modificada:

```bash
cp -r grbl ~/Arduino/libraries/grbl
```

Debe quedar asi:

```text
~/Arduino/libraries/grbl/config.h
~/Arduino/libraries/grbl/grbl.h
~/Arduino/libraries/grbl/cpu_map.h
```

## 6. Verificar que Arduino IDE usara el config.h correcto

Comprobar que existe:

```bash
ls ~/Arduino/libraries/grbl
```

Comprobar la modificacion de homing:

```bash
grep -n "HOMING_CYCLE" ~/Arduino/libraries/grbl/config.h
```

La salida debe incluir algo parecido a:

```c
#define HOMING_CYCLE_0 ((1<<X_AXIS)|(1<<Y_AXIS))
// #define HOMING_CYCLE_1
```

Si hay varias copias de GRBL en la computadora, buscarlas con:

```bash
find ~ -path "*/libraries/grbl/config.h" 2>/dev/null
```

Arduino IDE usara la copia que este dentro de la carpeta configurada en:

```text
File > Preferences > Sketchbook location
```

## 7. Abrir grblUpload

Cerrar y volver a abrir Arduino IDE.

Luego abrir:

```text
File > Examples > grbl > grblUpload
```

El archivo `grblUpload.ino` se vera casi vacio. Eso es normal.

Debe contener algo como:

```cpp
#include <grbl.h>

// Do not alter this file!
```

No hay que agregar nada mas. Ese archivo solo sirve para compilar y cargar todo GRBL al Arduino.

## 8. Seleccionar placa y puerto

En Arduino IDE:

```text
Tools > Board > Arduino Uno
Tools > Port > /dev/ttyACM0
```

El puerto puede variar. Tambien podria aparecer como:

```text
/dev/ttyUSB0
```

## 9. Cargar GRBL

Con `grblUpload.ino` abierto, presionar:

```text
Upload
```

Al terminar, el Arduino Uno queda funcionando como controlador GRBL.

## 10. Verificar desde Serial Monitor

Abrir:

```text
Tools > Serial Monitor
```

Configurar:

```text
115200 baud
Newline
```

Tambien puede usarse:

```text
115200 baud
Both NL & CR
```

Presionar reset en el Arduino.

Debe aparecer:

```text
Grbl 1.1h ['$' for help]
```

Luego escribir:

```text
$$
```

GRBL debe responder con la lista de parametros, por ejemplo:

```text
$0=10
$1=25
$2=0
$3=0
...
$100=250.000
$101=250.000
$102=250.000
...
ok
```

Si responde con la configuracion y `ok`, el firmware esta cargado correctamente.

## 11. Configuraciones que se ajustaran despues

No es necesario ajustar todavia:

```text
pasos por mm
direccion de motores
velocidad maxima
aceleracion
limites duros
homing
area real de dibujo
offset artistico
```

Eso se ajustara despues con UGS o bCNC, cuando ya esten conectados:

```text
CNC Shield
drivers A4988
motores
sensores de limite
fuente de alimentacion
```

Los parametros se cambiaran con comandos de GRBL como:

```text
$100=...
$101=...
$110=...
$111=...
$120=...
$121=...
$21=...
$22=...
$23=...
```

## 12. Estado esperado al terminar

Al final de este proceso debe cumplirse:

```text
Arduino Uno carga correctamente grblUpload
Serial Monitor muestra Grbl 1.1h
El comando $$ devuelve configuracion
La configuracion termina con ok
```

Con eso queda lista la primera etapa: firmware GRBL instalado.

La siguiente etapa es conectar el CNC Shield con un solo driver A4988 y un solo motor para hacer pruebas de movimiento controladas desde UGS o bCNC.
