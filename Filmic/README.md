# Filmic

`Filmic/` es el módulo encargado de ejecutar físicamente el archivo `drawing.gcode` generado por `Drawing/` y enviarlo a GRBL por puerto serial.

Este módulo no analiza fotos, no lee sensores ambientales, no genera SVG, no genera preview y no produce G-code. Su función es tomar un G-code existente dentro de una sesión y transmitirlo a la máquina de dibujo.

## Flujo actual del sistema

```text
OLED + botones
→ Node-RED por UDP 5005
→ Drawing genera drawing.gcode
→ Filmic ejecuta drawing.gcode en GRBL
→ OLED recibe estado/progreso por UDP 5006
```

La ejecución desde OLED ya queda integrada mediante el comando:

```text
Ejecutar dibujo
```

Node-RED recibe el comando, prepara los argumentos de ejecución, llama a `Filmic/execute_drawing.py` y procesa el progreso que Filmic imprime por `stdout`.

## Estructura de sesiones

Los datos de sesión viven fuera del repositorio, en:

```text
/home/pi/data
```

Cada sesión tiene esta estructura:

```text
/home/pi/data/sessions/<SESSION_ID>/
├── photos/
├── environment/
└── output/
    ├── drawing.svg
    ├── drawing.gcode
    ├── preview.png
    ├── metadata.json
    ├── generation_log.json
    └── process_steps/
```

Ejemplo para `S01`:

```text
/home/pi/data/sessions/S01/output/drawing.gcode
```

Filmic espera que el archivo `drawing.gcode` ya exista antes de ejecutar.

## Convención física actual

La máquina está configurada para trabajar con origen en la esquina inferior izquierda del área de dibujo.

```text
Origen: esquina inferior izquierda
X positivo: hacia la derecha
Y positivo: hacia arriba
```

En esta máquina, el eje Y corresponde al movimiento de la plancha de dibujo.

La navegación manual en GRBL debe respetar esto:

```text
Flecha izquierda  → el porta plumas se mueve a la izquierda
Flecha derecha    → el porta plumas se mueve a la derecha
Flecha arriba     → la plancha sube
Flecha abajo      → la plancha baja
```

Si los movimientos manuales ya respetan esa lógica, no se debe modificar `$3`.

## Homing actual requerido

El homing debe terminar en la esquina inferior izquierda.

```text
X busca izquierda
Y baja la plancha
```

Después del homing, `execute_drawing.py` establece el cero de trabajo con:

```gcode
G10 L20 P1 X0 Y0
```

Esto hace que la posición alcanzada por el homing se convierta en `X0 Y0`, que corresponde al inicio del dibujo desde la esquina inferior izquierda.

## Relación con Drawing

Para esta configuración física, en `Drawing/drawing_config.py` debe mantenerse:

```python
gcode_y_mode = "flip"
```

La razón es que el sistema de imagen y el sistema físico usan Y en sentidos opuestos:

```text
Imagen:
Y = 0 arriba
Y = altura abajo

Máquina:
Y = 0 abajo
Y = altura arriba
```

`flip` convierte las coordenadas de imagen al sistema de coordenadas físico de la máquina.

No cambiar a `direct` mientras se mantenga el origen físico en la esquina inferior izquierda.

## Preparar entorno virtual de Filmic

Desde la Raspberry Pi:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

rm -rf .venv

sudo apt update
sudo apt install -y python3-venv

python3 -m venv --system-site-packages .venv

source .venv/bin/activate

python -m pip install --upgrade pip
pip install pyserial
```

Verificar instalación:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic
source .venv/bin/activate

python - <<'PY'
import serial
print("Filmic OK")
print("pyserial:", serial.__version__)
PY
```

## Puerto serial de GRBL

Revisar qué puerto tiene el Arduino/GRBL:

```bash
ls -lah /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Puertos comunes:

```text
/dev/ttyACM0
/dev/ttyUSB0
```

El usuario `pi` debe pertenecer al grupo `dialout`:

```bash
groups pi
```

Debe aparecer:

```text
dialout
```

Si no aparece:

```bash
sudo usermod -aG dialout pi
sudo reboot
```

## Configuración importante de GRBL

Parámetros relevantes:

```text
$3   = dirección normal de movimiento
$21  = límites duros
$22  = homing
$23  = dirección de homing
$27  = separación después del homing
$100 = pasos/mm de X
$101 = pasos/mm de Y
```

Durante pruebas, los límites duros pueden estar apagados:

```text
$21=0
```

El homing debe estar activado:

```text
$22=1
```

Los pasos por milímetro se calibran con:

```text
$100=...
$101=...
```

## Leer configuración actual de GRBL

Usar este comando para leer `$3`, `$21`, `$22`, `$23`, `$27`, `$100` y `$101`:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
import serial, time

PORT = "/dev/ttyACM0"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(2)
    ser.write(b"\r\n\r\n")
    time.sleep(1)
    ser.reset_input_buffer()

    ser.write(b"$$\n")
    time.sleep(0.5)

    print("=== VALORES IMPORTANTES ===")

    while True:
        line = ser.readline().decode(errors="replace").strip()
        if (
            line.startswith("$3=") or
            line.startswith("$21=") or
            line.startswith("$22=") or
            line.startswith("$23=") or
            line.startswith("$27=") or
            line.startswith("$100=") or
            line.startswith("$101=")
        ):
            print(line)
        if line == "ok":
            break
PY
```

Si el puerto no es `/dev/ttyACM0`, cambiar la variable `PORT`.

## Dirección normal de movimiento: `$3`

`$3` controla la dirección normal de movimiento de los ejes.

No modificar `$3` si la navegación manual ya funciona así:

```text
Izquierda → porta plumas a la izquierda
Derecha   → porta plumas a la derecha
Arriba    → plancha hacia arriba
Abajo     → plancha hacia abajo
```

En este proyecto, los movimientos manuales ya estaban correctos. Por eso no se modificó `$3`.

## Dirección de homing: `$23`

`$23` controla hacia dónde busca la máquina durante el homing.

Para este proyecto se necesitaba cambiar únicamente el homing de Y:

```text
Antes:
Y subía durante homing

Ahora:
Y baja durante homing
```

El eje Y corresponde al bit `2`. Para invertir solo el homing de Y:

```text
nuevo $23 = $23 actual ^ 2
```

Tabla rápida:

```text
$23 actual → nuevo $23

0 → 2
1 → 3
2 → 0
3 → 1
4 → 6
5 → 7
6 → 4
7 → 5
```

Comando para leer `$23`, invertir solo el bit de Y y guardar el nuevo valor:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
import serial, time, re

PORT = "/dev/ttyACM0"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(2)
    ser.write(b"\r\n\r\n")
    time.sleep(1)
    ser.reset_input_buffer()

    ser.write(b"$$\n")
    time.sleep(0.5)

    current_23 = None

    while True:
        line = ser.readline().decode(errors="replace").strip()
        m = re.match(r"\$23=(\d+)", line)
        if m:
            current_23 = int(m.group(1))
            print("Actual:", line)
        if line == "ok":
            break

    if current_23 is None:
        raise SystemExit("No pude leer $23")

    new_23 = current_23 ^ 2

    cmd = f"$23={new_23}"
    print("Nuevo:", cmd)

    ser.write((cmd + "\n").encode())
    time.sleep(0.5)

    while ser.in_waiting:
        print(ser.readline().decode(errors="replace").strip())
PY
```

## Separación después del homing: `$27`

`$27` define cuánto se separa la máquina del switch después de hacer homing.

Si después del homing la máquina queda muy pegada al limit switch, se puede usar:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
import serial, time

PORT = "/dev/ttyACM0"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(2)
    ser.write(b"\r\n\r\n")
    time.sleep(1)
    ser.reset_input_buffer()

    for cmd in ["$27=3.000"]:
        print(">", cmd)
        ser.write((cmd + "\n").encode())
        time.sleep(0.5)
        while ser.in_waiting:
            print(ser.readline().decode(errors="replace").strip())
PY
```

Si todavía queda demasiado cerca del switch, probar:

```text
$27=5.000
```

## Probar homing

Antes de ejecutar dibujos completos, probar solo homing:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
import serial, time

PORT = "/dev/ttyACM0"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(2)
    ser.write(b"\r\n\r\n")
    time.sleep(1)
    ser.reset_input_buffer()

    print("> $H")
    ser.write(b"$H\n")

    start = time.time()
    while time.time() - start < 60:
        line = ser.readline().decode(errors="replace").strip()
        if line:
            print(line)
        if line == "ok":
            break
PY
```

Resultado esperado:

```text
X busca izquierda
Y baja la plancha
La máquina termina en la esquina inferior izquierda
GRBL responde ok
```

## Verificar que existe el G-code

Antes de ejecutar, confirmar que existe el archivo:

```bash
ls -lah /home/pi/data/sessions/S01/output/drawing.gcode
```

Verificar que Python de Filmic lo puede leer:

```bash
cd /home/pi/Documents/GitHub/contraespacios/Filmic

/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
from pathlib import Path

p = Path("/home/pi/data/sessions/S01/output/drawing.gcode")

print("path:", p)
print("exists:", p.exists())
print("is_file:", p.is_file())

if p.exists():
    print("size:", p.stat().st_size)
    print("primeras lineas:")
    print("\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:10]))
else:
    print("NO LO VE PYTHON")
PY
```

## Prueba segura con puerto falso

Esta prueba confirma que Filmic encuentra el G-code sin mover la máquina:

```bash
/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 \
/home/pi/Documents/GitHub/contraespacios/Filmic/execute_drawing.py \
--session S01 \
--data-root /home/pi/data \
--gcode /home/pi/data/sessions/S01/output/drawing.gcode \
--port /dev/ttyFAKE \
--baud 115200 \
--startup-delay 2 \
--homing-timeout 60 \
--set-work-zero \
--homing
```

Resultado esperado:

```text
Conectando /dev/ttyFAKE
could not open port /dev/ttyFAKE
```

Ese error es correcto. Significa que Filmic encontró el G-code y falló únicamente porque el puerto falso no existe.

## Ejecutar dibujo manualmente

Con el Arduino/GRBL conectado, revisar el puerto:

```bash
ls -lah /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Ejecutar con homing:

```bash
/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 \
/home/pi/Documents/GitHub/contraespacios/Filmic/execute_drawing.py \
--session S01 \
--data-root /home/pi/data \
--gcode /home/pi/data/sessions/S01/output/drawing.gcode \
--port /dev/ttyACM0 \
--baud 115200 \
--startup-delay 2 \
--homing-timeout 60 \
--set-work-zero \
--homing
```

Ejecutar sin homing:

```bash
/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 \
/home/pi/Documents/GitHub/contraespacios/Filmic/execute_drawing.py \
--session S01 \
--data-root /home/pi/data \
--gcode /home/pi/data/sessions/S01/output/drawing.gcode \
--port /dev/ttyACM0 \
--baud 115200 \
--startup-delay 2 \
--homing-timeout 60 \
--set-work-zero \
--no-homing
```

En modo `--no-homing`, la posición actual se toma como cero de trabajo. La punta debe colocarse manualmente en el origen antes de ejecutar.

## Opciones de `execute_drawing.py`

```text
--session           ID de sesión. Ejemplo: S01
--data-root         Carpeta raíz de datos. Default: /home/pi/data
--gcode             Ruta explícita al archivo drawing.gcode
--port              Puerto serial. Ejemplo: /dev/ttyACM0
--baud              Baudrate serial. Default: 115200
--startup-delay     Espera inicial después de abrir puerto
--homing            Ejecuta $H antes de dibujar
--no-homing         No ejecuta $H
--homing-timeout    Timeout para homing
--set-work-zero     Define la posición actual como X0 Y0
--no-set-work-zero  No define cero de trabajo
--unlock            Ejecuta $X antes de dibujar
```

En operación normal se recomienda:

```text
--homing
--set-work-zero
```

No se recomienda usar `--unlock` como rutina normal, salvo para pruebas específicas. Es mejor resolver homing y alarmas correctamente.

## Integración con Node-RED

El nodo `exec` de Node-RED debe ejecutar:

```bash
/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 -u /home/pi/Documents/GitHub/contraespacios/Filmic/execute_drawing.py
```

Configuración del nodo `exec`:

```text
Append msg.payload: activado
Use spawn: activado
Timeout: vacío o 0
```

El parámetro `-u` permite que Python mande progreso en tiempo real por `stdout`.

El payload enviado desde Node-RED debe quedar así:

```text
--session S01 --data-root /home/pi/data --gcode /home/pi/data/sessions/S01/output/drawing.gcode --baud 115200 --startup-delay 2 --homing-timeout 60 --set-work-zero --homing --port /dev/ttyACM0
```

No usar comillas simples manuales alrededor de las rutas cuando el nodo `exec` usa `Use spawn`.

Correcto:

```text
--data-root /home/pi/data
```

Evitar:

```text
--data-root '/home/pi/data'
```

## Nodo `preparar_execute_drawing`

Function node con 2 salidas:

```text
Salida 1 → UDP out OLED 5006
Salida 2 → exec Filmic execute_drawing.py
```

Código:

```js
// preparar_execute_drawing
// Salida 1: mensaje inmediato a OLED
// Salida 2: argumentos para ejecutar Filmic/execute_drawing.py

if (flow.get("execution_busy")) {
    var busyMsg = {
        payload: JSON.stringify({
            type: "status",
            session_id: flow.get("execution_session") || flow.get("active_session") || "S01",
            step: "execute",
            state: "running",
            message: "Ya esta dibujando",
            progress: flow.get("execution_progress") || 0
        }),
        ip: "127.0.0.1",
        host: "127.0.0.1",
        port: 5006
    };

    return [busyMsg, null];
}

var input = msg.payload || {};

var sessionId =
    input.session_id ||
    input.active_session ||
    flow.get("active_session") ||
    "S01";

sessionId = String(sessionId).trim();

flow.set("active_session", sessionId);
flow.set("execution_busy", true);
flow.set("execution_session", sessionId);
flow.set("execution_progress", 0);
flow.set("execution_had_error", false);

// Para prueba segura usar:
// var SERIAL_PORT = "/dev/ttyFAKE";

// Para operación normal usar el puerto real:
var SERIAL_PORT = "/dev/ttyACM0";

// También se puede dejar vacío para autodetección:
// var SERIAL_PORT = "";

var USE_HOMING = true;
var USE_UNLOCK = false;

var DATA_ROOT = "/home/pi/data";
var GCODE_PATH = DATA_ROOT + "/sessions/" + sessionId + "/output/drawing.gcode";

var args = [
    "--session", sessionId,
    "--data-root", DATA_ROOT,
    "--gcode", GCODE_PATH,
    "--baud", "115200",
    "--startup-delay", "2",
    "--homing-timeout", "60",
    "--set-work-zero"
];

if (USE_HOMING) {
    args.push("--homing");
} else {
    args.push("--no-homing");
}

if (USE_UNLOCK) {
    args.push("--unlock");
}

if (SERIAL_PORT && SERIAL_PORT.trim() !== "") {
    args.push("--port", SERIAL_PORT.trim());
}

var oledMsg = {
    payload: JSON.stringify({
        type: "status",
        session_id: sessionId,
        step: "execute",
        state: "running",
        message: "Iniciando dibujo",
        progress: 0,
        session_has_drawing: true
    }),
    ip: "127.0.0.1",
    host: "127.0.0.1",
    port: 5006
};

var execMsg = {
    payload: args.join(" "),
    session_id: sessionId,
    gcode_path: GCODE_PATH
};

node.status({
    fill: "yellow",
    shape: "dot",
    text: "Film " + sessionId
});

return [oledMsg, execMsg];
```

## Nodo `procesar_stdout_execute`

Conectar a salida 1 del nodo `exec`.

Function node con 1 salida:

```text
stdout del exec → procesar_stdout_execute → UDP out OLED 5006
```

Código:

```js
// procesar_stdout_execute
// Procesa las lineas JSON que Filmic imprime por stdout.
// Filmic debe emitir lineas tipo execute_progress y execute_result.

var text = "";

if (typeof Buffer !== "undefined" && Buffer.isBuffer(msg.payload)) {
    text = msg.payload.toString("utf8");
} else {
    text = String(msg.payload || "");
}

var buffer = context.get("buffer") || "";
text = buffer + text;

var lines = text.split(/\r?\n/);
context.set("buffer", lines.pop() || "");

var out = [];

for (var i = 0; i < lines.length; i++) {
    var line = String(lines[i] || "").trim();

    if (!line) {
        continue;
    }

    var data = {};

    try {
        data = JSON.parse(line);
    } catch (err) {
        node.warn("stdout no JSON: " + line);
        continue;
    }

    var sessionId =
        data.session_id ||
        msg.session_id ||
        flow.get("execution_session") ||
        flow.get("active_session") ||
        "S01";

    var progress = parseInt(data.progress || 0, 10);

    if (isNaN(progress)) {
        progress = 0;
    }

    progress = Math.max(0, Math.min(100, progress));

    flow.set("execution_progress", progress);

    if (data.ok === false || data.state === "error") {
        flow.set("execution_busy", false);
        flow.set("executed_done", false);
        flow.set("execution_had_error", true);

        out.push({
            payload: JSON.stringify({
                type: "status",
                session_id: sessionId,
                step: "execute",
                state: "error",
                message: data.message || data.error || "Error al dibujar",
                progress: progress,
                drawing: true,
                drawing_done: true,
                gcode_done: true,
                executed: false,
                executed_done: false,
                session_has_drawing: true
            }),
            ip: "127.0.0.1",
            host: "127.0.0.1",
            port: 5006
        });

        node.status({
            fill: "red",
            shape: "ring",
            text: "error " + sessionId
        });

        continue;
    }

    if (data.type === "execute_result" && data.state === "done") {
        flow.set("execution_busy", false);
        flow.set("executed_done", true);
        flow.set("execution_progress", 100);
        flow.set("execution_had_error", false);

        out.push({
            payload: JSON.stringify({
                type: "framework_state",
                session_id: sessionId,
                step: "execute",
                state: "done",
                message: data.message || "Dibujo ejecutado",
                progress: 100,

                drawing: true,
                drawing_done: true,
                gcode_done: true,

                executed: true,
                executed_done: true,
                drawing_executed: true,
                session_has_drawing: true,

                lines_sent: data.lines_sent || null,
                serial_port: data.port || null,
                gcode_path: data.gcode || null
            }),
            ip: "127.0.0.1",
            host: "127.0.0.1",
            port: 5006
        });

        node.status({
            fill: "green",
            shape: "dot",
            text: sessionId + " ejecutado"
        });

        continue;
    }

    out.push({
        payload: JSON.stringify({
            type: "status",
            session_id: sessionId,
            step: "execute",
            state: data.state || "running",
            message: data.message || "Dibujando",
            progress: progress,

            drawing: true,
            drawing_done: true,
            gcode_done: true,

            executed: false,
            executed_done: false,
            session_has_drawing: true
        }),
        ip: "127.0.0.1",
        host: "127.0.0.1",
        port: 5006
    });

    node.status({
        fill: "yellow",
        shape: "dot",
        text: sessionId + " " + progress + "%"
    });
}

if (out.length === 0) {
    return null;
}

return [out];
```

## Nodo `procesar_stderr_execute`

Conectar a salida 2 del nodo `exec`.

```text
stderr del exec → procesar_stderr_execute → UDP out OLED 5006
```

Código:

```js
// procesar_stderr_execute
// Maneja stderr del proceso Filmic.

var errorText = "";

if (typeof Buffer !== "undefined" && Buffer.isBuffer(msg.payload)) {
    errorText = msg.payload.toString("utf8");
} else {
    errorText = String(msg.payload || "");
}

errorText = errorText.trim();

if (!errorText) {
    return null;
}

flow.set("execution_busy", false);
flow.set("executed_done", false);
flow.set("execution_had_error", true);

var sessionId =
    msg.session_id ||
    flow.get("execution_session") ||
    flow.get("active_session") ||
    "S01";

node.warn(errorText);

node.status({
    fill: "red",
    shape: "ring",
    text: "stderr Filmic"
});

msg.payload = JSON.stringify({
    type: "status",
    session_id: sessionId,
    step: "execute",
    state: "error",
    message: errorText.slice(0, 40),
    progress: flow.get("execution_progress") || 0,
    executed: false,
    executed_done: false,
    session_has_drawing: true
});

msg.ip = "127.0.0.1";
msg.host = "127.0.0.1";
msg.port = 5006;

return msg;
```

## Nodo `procesar_cierre_execute`

Conectar a salida 3 del nodo `exec`.

```text
cierre del exec → procesar_cierre_execute → UDP out OLED 5006
```

Este nodo evita duplicar errores si `stdout` o `stderr` ya mandaron un error específico.

Código:

```js
// procesar_cierre_execute
// Revisa el codigo de salida del proceso exec.
// Si stdout/stderr ya reportaron error, no duplica el mensaje.

var code = 0;
var signal = "";

if (typeof msg.payload === "object" && msg.payload !== null) {
    code = Number(msg.payload.code || 0);
    signal = String(msg.payload.signal || "");
} else {
    code = Number(msg.payload || 0);
}

var sessionId =
    msg.session_id ||
    flow.get("execution_session") ||
    flow.get("active_session") ||
    "S01";

if (code === 0 && !signal) {
    node.status({
        fill: "green",
        shape: "dot",
        text: "proceso OK"
    });

    return null;
}

if (flow.get("execution_had_error")) {
    node.status({
        fill: "red",
        shape: "ring",
        text: "error ya reportado"
    });

    return null;
}

flow.set("execution_busy", false);
flow.set("executed_done", false);
flow.set("execution_had_error", true);

node.status({
    fill: "red",
    shape: "ring",
    text: "exit " + (code || signal)
});

msg.payload = JSON.stringify({
    type: "status",
    session_id: sessionId,
    step: "execute",
    state: "error",
    message: signal ? "Proceso detenido " + signal : "Proceso termino con codigo " + code,
    progress: flow.get("execution_progress") || 0,
    executed: false,
    executed_done: false,
    session_has_drawing: true
});

msg.ip = "127.0.0.1";
msg.host = "127.0.0.1";
msg.port = 5006;

return msg;
```

## Conexiones en Node-RED

La cadena debe quedar así:

```text
switch command execute_drawing
        ↓
execute_drawing
        ↓
preparar_execute_drawing
   salida 1 → udp out OLED 5006
   salida 2 → exec Filmic execute_drawing.py
                    salida 1 stdout → procesar_stdout_execute → udp out OLED 5006
                    salida 2 stderr → procesar_stderr_execute → udp out OLED 5006
                    salida 3 cierre → procesar_cierre_execute → udp out OLED 5006
```

El nodo `execute_drawing` debe conservar la sesión activa y no destruir el payload original.

Código sugerido:

```js
// execute_drawing
// Conserva la sesión activa y prepara el comando para Filmic.

var input = msg.payload || {};

var sessionId =
    input.session_id ||
    input.active_session ||
    flow.get("active_session") ||
    "S01";

var hasDrawing =
    input.session_has_drawing === true ||
    flow.get("session_has_drawing") === true ||
    flow.get("drawing_done") === true;

flow.set("active_session", sessionId);

msg.payload = {
    type: "command",
    command: "execute_drawing",
    session_id: sessionId,
    active_session: sessionId,
    session_has_drawing: hasDrawing
};

node.status({
    fill: "blue",
    shape: "dot",
    text: "ejecutar " + sessionId
});

return msg;
```

## Reiniciar Node-RED

Después de modificar nodos:

```bash
node-red-restart
```

Después de reiniciar Node-RED, correr de nuevo la OLED:

```bash
cd /home/pi/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

## Progreso esperado en Node-RED

Durante ejecución, Filmic manda mensajes JSON por `stdout`.

Ejemplo de progreso:

```json
{"type":"status","session_id":"S01","step":"execute","state":"running","message":"Dibujando 50%","progress":50}
```

Ejemplo de resultado correcto:

```json
{"type":"framework_state","session_id":"S01","step":"execute","state":"done","message":"Dibujo ejecutado","progress":100}
```

## Errores comunes

### `No existe el G-code`

Verificar que exista:

```bash
ls -lah /home/pi/data/sessions/S01/output/drawing.gcode
```

Verificar que Python de Filmic lo pueda leer:

```bash
/home/pi/Documents/GitHub/contraespacios/Filmic/.venv/bin/python3 - <<'PY'
from pathlib import Path
p = Path("/home/pi/data/sessions/S01/output/drawing.gcode")
print("exists:", p.exists())
print("is_file:", p.is_file())
PY
```

Si Python lo ve pero Node-RED no, revisar que el payload no tenga comillas mal pasadas y que se esté enviando explícitamente:

```text
--gcode /home/pi/data/sessions/S01/output/drawing.gcode
```

### `could not open port /dev/ttyFAKE`

Es un error esperado si se está usando el puerto falso para prueba segura.

Cambiar a puerto real:

```text
/dev/ttyACM0
```

o:

```text
/dev/ttyUSB0
```

### `GRBL no respondió dentro del tiempo esperado`

Puede ocurrir si:

```text
La máquina activó un limit switch durante el dibujo.
Hubo un salto mecánico.
GRBL entró en alarma.
Se perdió comunicación serial.
Un movimiento quedó bloqueado físicamente.
Un comando final no recibió respuesta.
```

Si ocurre casi al final del dibujo, revisar especialmente:

```text
limit switch de Y
separación después del homing
valor $27
saltos mecánicos de la plancha
ruido eléctrico en switches o motores
```

### La máquina homea arriba en lugar de abajo

No cambiar `$3` si los movimientos manuales ya son correctos.

Cambiar únicamente `$23`, invirtiendo el bit de Y:

```text
nuevo $23 = $23 actual ^ 2
```

Después probar:

```gcode
$H
```

La máquina debe terminar en la esquina inferior izquierda.

### El dibujo sale invertido verticalmente

Confirmar primero que el homing termina abajo-izquierda.

Después revisar que en `Drawing/drawing_config.py` esté:

```python
gcode_y_mode = "flip"
```

No cambiar el modo de Y mientras el problema sea físico o de homing.

## Secuencia recomendada de prueba

```text
1. Generar dibujo desde OLED.
2. Confirmar que existe drawing.gcode.
3. Probar Filmic con /dev/ttyFAKE.
4. Confirmar que el único error sea el puerto falso.
5. Probar homing con $H.
6. Confirmar que el homing termina abajo-izquierda.
7. Ejecutar dibujo manualmente desde terminal.
8. Ejecutar dibujo desde OLED.
```

## Estado funcional esperado

Cuando todo está correcto:

```text
OLED genera el dibujo.
Drawing crea drawing.gcode.
OLED ejecuta el dibujo.
Node-RED llama a Filmic.
Filmic hace homing abajo-izquierda.
Filmic define X0 Y0.
GRBL ejecuta el G-code.
OLED muestra progreso.
La máquina dibuja desde la esquina inferior izquierda.
```

## Notas de Git

Los datos de sesión no deben guardarse en el repositorio.

Mantener separado:

```text
/home/pi/data
```

del código:

```text
/home/pi/Documents/GitHub/contraespacios
```

Así se puede hacer `git pull`, cambiar scripts o actualizar documentación sin borrar fotos, JSON, previews o G-code generados.
