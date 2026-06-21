# OLED UDP mensajes completo · Contra Espacios

Documento de referencia para los mensajes UDP entre la interfaz OLED, Node-RED y los módulos del framework de Contra Espacios.

La OLED no guarda fotos ni lecturas directamente. La OLED define la sesión activa y manda comandos a Node-RED. Node-RED debe guardar los archivos usando `session_id`.

---

## Puertos principales

| Dirección | Host | Puerto | Uso |
|---|---|---:|---|
| OLED -> Node-RED | `127.0.0.1` | `5005` | Comandos desde pantalla |
| Node-RED -> OLED | `127.0.0.1` | `5006` | Estado y progreso |
| Node-RED -> ESP32 ambiental | `contraenv.local` | `4210` | Pedir lectura ambiental |
| ESP32 ambiental -> Node-RED | IP Raspberry | `5010` | Lectura/progreso ambiental |

---

## Datos persistentes

Ruta predeterminada:

```text
~/data
```

Estado global:

```text
~/data/state.json
```

Sesiones:

```text
~/data/sessions/S01/
~/data/sessions/S02/
...
~/data/sessions/S64/
```

Cada sesión contiene:

```text
session.json
photos/
environment/
output/
```

---

## Sesión activa

La OLED crea `S01` automáticamente si no existe ninguna sesión.

Archivo global:

```json
{
  "active_session": "S01",
  "last_session": "S01",
  "max_sessions": 64,
  "session_count": 1,
  "updated_at": "2026-06-21T05:28:00"
}
```

---

## Mensaje hello de la OLED

La OLED lo manda al arrancar:

```json
{
  "type": "hello",
  "message": "OLED interface online",
  "listen_port": 5006,
  "active_session": "S01",
  "session_id": "S01",
  "session_has_drawing": false,
  "data_root": "/home/pi/data",
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:28:00"
}
```

---

## Comandos desde OLED hacia Node-RED

Todos llegan por:

```text
UDP IN 5005
```

### Capturar foto

```json
{
  "type": "command",
  "command": "capture_photo",
  "label": "Capturar foto",
  "session_id": "S01",
  "active_session": "S01",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:28:00"
}
```

Node-RED debe guardar la foto en:

```text
~/data/sessions/S01/photos/photo_001.jpg
```

Respuesta sugerida a OLED:

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "photo": true,
  "photo_done": true,
  "photo_count": 1,
  "step": "photo",
  "state": "done",
  "message": "Foto guardada",
  "progress": 25
}
```

---

### Capturar ambiente

```json
{
  "type": "command",
  "command": "capture_environment",
  "label": "Capturar ambiente",
  "session_id": "S01",
  "active_session": "S01",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:29:00"
}
```

Node-RED debe pedir lectura al ESP32:

```json
{
  "type": "command",
  "command": "read_environment",
  "source": "node-red",
  "target": "contraenv",
  "session_id": "S01",
  "timestamp": "2026-06-21T05:29:00"
}
```

Hacia:

```text
contraenv.local:4210
```

Mientras espera, Node-RED puede mandar a OLED:

```json
{
  "type": "status",
  "session_id": "S01",
  "step": "environment",
  "state": "running",
  "message": "Leyendo ambiente",
  "progress": 30
}
```

Cuando llega lectura completa del ESP32, Node-RED debe guardar:

```text
~/data/sessions/S01/environment/env_001.json
```

Respuesta final a OLED:

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "environment": true,
  "environment_done": true,
  "environment_count": 1,
  "step": "environment",
  "state": "done",
  "message": "Ambiente listo",
  "progress": 50
}
```

Si la lectura está incompleta:

```json
{
  "type": "status",
  "session_id": "S01",
  "environment": false,
  "environment_done": false,
  "step": "environment",
  "state": "error",
  "message": "ENS no estable",
  "progress": 35
}
```

La OLED solo marca `A` como OK si `environment_done` es verdadero o si `environment_count > 0`.

---

### Nueva sesión

```json
{
  "type": "command",
  "command": "new_session",
  "label": "Nueva sesion",
  "session_id": "S02",
  "active_session": "S02",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:40:00"
}
```

La OLED crea la carpeta y actualiza:

```text
~/data/state.json
```

Node-RED puede usar este mensaje para actualizar variables internas:

```javascript
flow.set("active_session", msg.payload.session_id);
```

---

### Seleccionar sesión

```json
{
  "type": "command",
  "command": "select_session",
  "label": "Seleccionar sesion",
  "session_id": "S03",
  "active_session": "S03",
  "session_has_drawing": true,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:42:00"
}
```

Node-RED debe guardar nuevas fotos o lecturas en la sesión seleccionada.

---

### Generar dibujo

```json
{
  "type": "command",
  "command": "generate_drawing",
  "label": "Generar dibujo",
  "session_id": "S03",
  "active_session": "S03",
  "session_has_drawing": false,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:45:00"
}
```

Node-RED o Python debe leer:

```text
~/data/sessions/S03/photos/
~/data/sessions/S03/environment/
```

y generar:

```text
~/data/sessions/S03/output/drawing.svg
~/data/sessions/S03/output/drawing.gcode
~/data/sessions/S03/output/metadata.json
```

Respuesta a OLED:

```json
{
  "type": "framework_state",
  "session_id": "S03",
  "drawing": true,
  "drawing_done": true,
  "session_has_drawing": true,
  "step": "drawing",
  "state": "done",
  "message": "Dibujo generado",
  "progress": 75
}
```

---

### Ejecutar dibujo

```json
{
  "type": "command",
  "command": "execute_drawing",
  "label": "Ejecutar dibujo",
  "session_id": "S03",
  "active_session": "S03",
  "session_has_drawing": true,
  "source": "contraespacios_oled",
  "timestamp": "2026-06-21T05:50:00"
}
```

Respuesta sugerida:

```json
{
  "type": "framework_state",
  "session_id": "S03",
  "executed": true,
  "executed_done": true,
  "step": "execute",
  "state": "done",
  "message": "Ejecucion lista",
  "progress": 100
}
```

---

## Mensajes que acepta la OLED desde Node-RED

Todos deben enviarse a:

```text
127.0.0.1:5006
```

### `type: status`

Uso: progreso o error sin necesariamente cerrar un paso.

```json
{
  "type": "status",
  "session_id": "S01",
  "step": "environment",
  "state": "running",
  "message": "Gases 14s",
  "progress": 42
}
```

### `type: framework_state`

Uso: actualizar estado general.

```json
{
  "type": "framework_state",
  "session_id": "S01",
  "photo_done": true,
  "environment_done": true,
  "drawing_done": false,
  "gcode_done": false,
  "executed_done": false,
  "photo_count": 3,
  "environment_count": 3,
  "step": "environment",
  "state": "done",
  "message": "Ambiente listo",
  "progress": 50
}
```

Alias válidos:

```json
{
  "photo": true,
  "environment": true,
  "drawing": true,
  "gcode": true,
  "executed": true
}
```

son equivalentes a:

```json
{
  "photo_done": true,
  "environment_done": true,
  "drawing_done": true,
  "gcode_done": true,
  "executed_done": true
}
```

### `type: screen`

Uso: mostrar mensaje personalizado temporal.

```json
{
  "type": "screen",
  "title": "GUARDANDO",
  "message": "Foto 03 lista"
}
```

### `type: reset`

Uso: limpiar estado visual.

```json
{
  "type": "reset"
}
```

---

## Mensajes ambientales directos

La OLED también tolera mensajes directos `type: "environment"` si por error o por diseño llegan a `5006`.

Ejemplo progreso:

```json
{
  "type": "environment",
  "device": "contraenv",
  "state": "running",
  "stage": "ens_warmup",
  "message": "Gases 14s",
  "progress": 42
}
```

Ejemplo final correcto:

```json
{
  "type": "environment",
  "device": "contraenv",
  "state": "done",
  "stage": "complete",
  "message": "Ambiente listo",
  "progress": 50,
  "aht_ok": true,
  "ens_ok": true,
  "temperature": 26.5,
  "humidity": 47.0,
  "aqi": 1,
  "tvoc": 21,
  "eco2": 400
}
```

La OLED lo convierte internamente a `framework_state` solo si contiene todos los datos.

---

## Function básico para responder foto a OLED

Después de guardar una foto:

```javascript
const sessionId = flow.get("active_session") || msg.session_id || msg.payload.session_id || "S01";
const photoCount = flow.get(`photo_count_${sessionId}`) || 1;

flow.set("photo_done", true);

msg.payload = JSON.stringify({
    type: "framework_state",
    session_id: sessionId,
    photo: true,
    photo_done: true,
    photo_count: photoCount,
    step: "photo",
    state: "done",
    message: "Foto guardada",
    progress: 25
});

msg.ip = "127.0.0.1";
msg.host = "127.0.0.1";
msg.port = 5006;

return msg;
```

---

## Function para solicitar lectura ambiental al ESP32

Configurar con dos salidas:

```text
Salida 1 -> UDP OUT contraenv.local:4210
Salida 2 -> UDP OUT 127.0.0.1:5006
```

```javascript
const sessionId = msg.payload.session_id || msg.payload.active_session || flow.get("active_session") || "S01";
flow.set("active_session", sessionId);

const toEsp32 = {
    payload: JSON.stringify({
        type: "command",
        command: "read_environment",
        source: "node-red",
        target: "contraenv",
        session_id: sessionId,
        timestamp: new Date().toISOString()
    }),
    ip: "contraenv.local",
    host: "contraenv.local",
    port: 4210
};

const toOled = {
    payload: JSON.stringify({
        type: "status",
        session_id: sessionId,
        step: "environment",
        state: "running",
        message: "Leyendo ambiente",
        progress: 30,
        environment: false,
        environment_done: false
    }),
    ip: "127.0.0.1",
    host: "127.0.0.1",
    port: 5006
};

return [toEsp32, toOled];
```

---

## Function para recibir respuesta ambiental del ESP32

Va después de:

```text
UDP IN 5010 -> JSON
```

Configurar con dos salidas:

```text
Salida 1 -> datos ambientales para guardar
Salida 2 -> UDP OUT 127.0.0.1:5006
```

```javascript
const data = msg.payload;

if (!data || typeof data !== "object") {
    return [null, null];
}

if (data.type !== "environment") {
    return [null, null];
}

const sessionId = data.session_id || flow.get("active_session") || "S01";

const hasTemperature = data.temperature !== null && data.temperature !== undefined && !Number.isNaN(Number(data.temperature));
const hasHumidity = data.humidity !== null && data.humidity !== undefined && !Number.isNaN(Number(data.humidity));
const hasAQI = data.aqi !== null && data.aqi !== undefined && !Number.isNaN(Number(data.aqi));
const hasTVOC = data.tvoc !== null && data.tvoc !== undefined && !Number.isNaN(Number(data.tvoc));
const hasECO2 = data.eco2 !== null && data.eco2 !== undefined && !Number.isNaN(Number(data.eco2));

const hasAllValues =
    data.state === "done" &&
    data.stage === "complete" &&
    data.aht_ok === true &&
    data.ens_ok === true &&
    hasTemperature &&
    hasHumidity &&
    hasAQI &&
    hasTVOC &&
    hasECO2;

const dataOut = {
    ...msg,
    payload: {
        ok: hasAllValues,
        session_id: sessionId,
        type: data.type,
        device: data.device || "contraenv",
        hostname: data.hostname || "contraenv.local",
        ip: data.ip,
        state: data.state,
        stage: data.stage,
        message: data.message,
        progress: data.progress,
        aht_ok: data.aht_ok === true,
        ens_ok: data.ens_ok === true,
        temperature: hasTemperature ? Number(data.temperature) : null,
        humidity: hasHumidity ? Number(data.humidity) : null,
        ens_status: data.ens_status ?? null,
        aqi: hasAQI ? Number(data.aqi) : null,
        tvoc: hasTVOC ? Number(data.tvoc) : null,
        eco2: hasECO2 ? Number(data.eco2) : null,
        timestamp: new Date().toISOString()
    }
};

flow.set("last_environment_message", dataOut.payload);

if (data.state === "running") {
    return [
        dataOut,
        {
            payload: JSON.stringify({
                type: "status",
                session_id: sessionId,
                step: "environment",
                state: "running",
                message: data.message || "Leyendo ambiente",
                progress: data.progress || 35
            }),
            ip: "127.0.0.1",
            host: "127.0.0.1",
            port: 5006
        }
    ];
}

if (data.stage === "complete") {
    if (hasAllValues) {
        flow.set("environment_done", true);

        const environmentCount = flow.get(`environment_count_${sessionId}`) || 1;

        return [
            dataOut,
            {
                payload: JSON.stringify({
                    type: "framework_state",
                    session_id: sessionId,
                    environment: true,
                    environment_done: true,
                    environment_count: environmentCount,
                    step: "environment",
                    state: "done",
                    message: "Ambiente listo",
                    progress: 50
                }),
                ip: "127.0.0.1",
                host: "127.0.0.1",
                port: 5006
            }
        ];
    }

    flow.set("environment_done", false);

    let errorMessage = "Lectura incompleta";
    if (data.aht_ok !== true) {
        errorMessage = "Error temp/hum";
    } else if (data.ens_ok !== true) {
        errorMessage = "ENS no estable";
    } else if (!hasAQI || !hasTVOC || !hasECO2) {
        errorMessage = "Faltan gases";
    }

    return [
        dataOut,
        {
            payload: JSON.stringify({
                type: "status",
                session_id: sessionId,
                environment: false,
                environment_done: false,
                step: "environment",
                state: "error",
                message: errorMessage,
                progress: 35
            }),
            ip: "127.0.0.1",
            host: "127.0.0.1",
            port: 5006
        }
    ];
}

return [dataOut, null];
```

---

## Pruebas manuales

Escuchar comandos OLED:

```bash
nc -ul 5005
```

Enviar progreso a OLED:

```bash
echo '{"type":"status","session_id":"S01","step":"environment","state":"running","message":"Gases 14s","progress":42}' | nc -u -w1 127.0.0.1 5006
```

Enviar dibujo generado:

```bash
echo '{"type":"framework_state","session_id":"S01","drawing":true,"drawing_done":true,"session_has_drawing":true,"step":"drawing","state":"done","message":"Dibujo generado","progress":75}' | nc -u -w1 127.0.0.1 5006
```

