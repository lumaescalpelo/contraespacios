# filmic

Programa separado para ejecutar el G-code generado por `Drawing`.

`filmic` no analiza fotos, no genera SVG y no genera G-code. Solo hace esto:

```text
leer /home/pi/data/sessions/S01/output/drawing.gcode
conectar con GRBL por USB
hacer homing
poner cero de trabajo
enviar el G-code
reportar progreso para la pantalla OLED vía Node-RED
```

## 1. Instalar

Coloca esta carpeta, por ejemplo, en:

```text
~/Documents/GitHub/contraespacios/filmic
```

Instala dependencias:

```bash
cd ~/Documents/GitHub/contraespacios/filmic

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Si el usuario `pi` no tiene permiso para usar el puerto serial:

```bash
sudo usermod -a -G dialout $USER
sudo reboot
```

## 2. Requisito de datos

`Drawing` debe haber generado antes:

```text
/home/pi/data/sessions/S01/output/drawing.gcode
```

Puedes comprobarlo con:

```bash
ls -lh /home/pi/data/sessions/S01/output/drawing.gcode
```

## 3. Requisito de GRBL

GRBL debe estar cargado en el Arduino Uno y debe poder conectarse desde bCNC.

Para usar homing:

```text
$22=1
```

Tus sensores de home están en:

```text
-X = límite izquierdo
-Y = límite inferior
```

Si `$H` mueve un eje hacia el lado contrario, se corrige con `$23` en GRBL.

## 4. Prueba manual

Con homing:

```bash
cd ~/Documents/GitHub/contraespacios/filmic
source .venv/bin/activate

python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --homing \
  --set-work-zero
```

Indicando puerto:

```bash
python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --port /dev/ttyACM0 \
  --homing \
  --set-work-zero
```

Diagnóstico sin homing:

```bash
python3 execute_drawing.py \
  --session S01 \
  --data-root /home/pi/data \
  --no-homing \
  --set-work-zero
```

El programa imprime líneas JSON. Ejemplo:

```json
{"ok": true, "type": "execute_progress", "state": "running", "progress": 42}
```

Al terminar:

```json
{"ok": true, "type": "execute_result", "state": "done", "progress": 100, "drawing_executed": true}
```

## 5. Node-RED

Flujo recomendado:

```text
switch: execute_drawing
→ preparar_execute_drawing
→ exec filmic/execute_drawing.py
   → stdout → procesar_execute_stdout → UDP OLED
   → stderr → procesar_execute_error → UDP OLED
   → rc     → debug opcional
```

Nodo `exec`, comando:

```text
/home/pi/Documents/GitHub/contraespacios/filmic/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/filmic/execute_drawing.py
```

Activar:

```text
Append msg.payload
```

Para ver porcentaje en vivo, el nodo `exec` debe entregar stdout mientras el proceso se ejecuta. Si solo entrega salida al final, la pantalla solo verá el resultado final.

Funciones:

```text
node_red_examples/preparar_execute_drawing.js
node_red_examples/procesar_execute_stdout.js
node_red_examples/procesar_execute_error.js
```

## 6. Git

El `.gitignore` evita subir:

```text
.venv/
__pycache__/
data/
sessions/
output/
drawing.gcode
*.log
```

Así puedes hacer:

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
```

sin arrastrar archivos locales.
