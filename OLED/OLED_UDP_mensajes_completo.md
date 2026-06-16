# Contra Espacios - Mensajes UDP de la interfaz OLED

Este documento describe los mensajes que puede enviar y recibir el programa:

```text
OLED/oled-udp.py
```

El programa conecta la botonera y la pantalla OLED con Node-RED usando mensajes UDP locales.

---

## 1. Puertos usados

| Dirección | Puerto | Uso |
|---|---:|---|
| `127.0.0.1` | `5005` | El programa OLED envía mensajes hacia Node-RED |
| `127.0.0.1` | `5006` | El programa OLED recibe mensajes desde Node-RED |

---

## 2. Ejecutar el programa OLED

Desde la carpeta `OLED`:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

---

## 3. Escuchar lo que manda la OLED

En una terminal separada:

```bash
nc -ul 5005
```

Después, al usar la botonera, deben aparecer los mensajes JSON enviados por `oled-udp.py`.

---

# Mensajes que envía `oled-udp.py`

Estos mensajes salen desde el programa OLED hacia Node-RED.

Destino:

```text
127.0.0.1:5005
```

El programa agrega automáticamente estos campos:

```json
{
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

---

## 4. Mensaje al iniciar

Cuando el programa arranca, manda:

```json
{
  "type": "hello",
  "message": "OLED interface online",
  "listen_port": 5006,
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería registrar que la interfaz local está activa.

---

## 5. Capturar foto

Se manda cuando seleccionas **Capturar foto** en la OLED.

```json
{
  "type": "command",
  "command": "capture_photo",
  "label": "Capturar foto",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería llamar el flujo de captura con ESP32CAM.

---

## 6. Capturar ambiente

Se manda cuando seleccionas **Capturar ambiente**.

```json
{
  "type": "command",
  "command": "capture_environment",
  "label": "Capturar ambiente",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería llamar la lectura del sensor ambiental ENS160 + AHT2X.

---

## 7. Generar dibujo

Se manda cuando seleccionas **Generar dibujo**.

```json
{
  "type": "command",
  "command": "generate_drawing",
  "label": "Generar dibujo",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería llamar el proceso que genera SVG y G-code.

---

## 8. Ejecutar dibujo

Se manda cuando seleccionas **Ejecutar dibujo**.

```json
{
  "type": "command",
  "command": "execute_drawing",
  "label": "Ejecutar dibujo",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería llamar el flujo que envía G-code a GRBL.

---

## 9. Pedir estado

Se manda cuando seleccionas **Estado** o presionas el botón 5.

```json
{
  "type": "command",
  "command": "show_status",
  "label": "Estado",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Node-RED debería responder con el estado actual del framework.

---

## 10. Mensaje al cerrar

Cuando sales con `Ctrl+C`, manda:

```json
{
  "type": "bye",
  "message": "OLED interface offline",
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

---

## 11. Resumen de mensajes enviados por OLED

| Acción en pantalla | `type` | `command` | Node-RED debería hacer |
|---|---|---|---|
| Iniciar programa | `hello` | — | Registrar interfaz activa |
| Capturar foto | `command` | `capture_photo` | Capturar imagen con ESP32CAM |
| Capturar ambiente | `command` | `capture_environment` | Leer ENS160 + AHT2X |
| Generar dibujo | `command` | `generate_drawing` | Generar SVG/G-code |
| Ejecutar dibujo | `command` | `execute_drawing` | Enviar G-code a GRBL |
| Ver estado | `command` | `show_status` | Responder estado actual |
| Cerrar programa | `bye` | — | Registrar cierre |

---

# Mensajes que espera recibir `oled-udp.py`

Estos mensajes deben salir desde Node-RED hacia el programa OLED.

Destino:

```text
127.0.0.1:5006
```

---

## 12. Estado general

Sirve para actualizar la pantalla de estado.

```json
{
  "type": "status",
  "step": "photo",
  "state": "running",
  "message": "Capturando foto",
  "progress": 25
}
```

### Comando de terminal

```bash
echo '{"type":"status","step":"photo","state":"running","message":"Capturando foto","progress":25}' | nc -u -w1 127.0.0.1 5006
```

---

## 13. Progreso

Sirve para reportar avance de una tarea.

```json
{
  "type": "progress",
  "step": "drawing",
  "state": "running",
  "message": "Generando SVG",
  "progress": 60
}
```

### Comando de terminal

```bash
echo '{"type":"progress","step":"drawing","state":"running","message":"Generando SVG","progress":60}' | nc -u -w1 127.0.0.1 5006
```

---

## 14. Estado completo del framework

Sirve para marcar qué partes del flujo ya están listas.

```json
{
  "type": "framework_state",
  "photo": true,
  "environment": true,
  "drawing": false,
  "gcode": false,
  "executed": false,
  "message": "Foto y ambiente listos",
  "progress": 40
}
```

### Comando de terminal

```bash
echo '{"type":"framework_state","photo":true,"environment":true,"drawing":false,"gcode":false,"executed":false,"message":"Foto y ambiente listos","progress":40}' | nc -u -w1 127.0.0.1 5006
```

---

## 15. Mensaje directo en pantalla

Sirve para mostrar una pantalla personalizada.

```json
{
  "type": "screen",
  "title": "FOTO",
  "message": "Captura lista"
}
```

### Comando de terminal

```bash
echo '{"type":"screen","title":"FOTO","message":"Captura lista"}' | nc -u -w1 127.0.0.1 5006
```

---

## 16. Reiniciar estado local

Limpia el estado interno de la interfaz OLED.

```json
{
  "type": "reset"
}
```

### Comando de terminal

```bash
echo '{"type":"reset"}' | nc -u -w1 127.0.0.1 5006
```

---

## 17. Campos que puede recibir la OLED

| Campo | Tipo | Uso |
|---|---|---|
| `type` | texto | Define el tipo de mensaje |
| `step` | texto | Paso actual del sistema |
| `state` | texto | Estado del paso |
| `message` | texto | Mensaje corto para mostrar |
| `progress` | número | Progreso de 0 a 100 |
| `photo` | booleano | Marca foto como lista |
| `photo_done` | booleano | Igual que `photo` |
| `environment` | booleano | Marca ambiente como listo |
| `environment_done` | booleano | Igual que `environment` |
| `drawing` | booleano | Marca dibujo como listo |
| `drawing_done` | booleano | Igual que `drawing` |
| `gcode` | booleano | Marca G-code como listo |
| `gcode_done` | booleano | Igual que `gcode` |
| `executed` | booleano | Marca ejecución como lista |
| `executed_done` | booleano | Igual que `executed` |
| `title` | texto | Título para mensajes tipo `screen` |

---

## 18. Valores sugeridos para `step`

| `step` | Significado |
|---|---|
| `inicio` | Sistema iniciado |
| `photo` | Captura de foto |
| `environment` | Lectura ambiental |
| `drawing` | Generación de dibujo/SVG |
| `gcode` | Generación de G-code |
| `execute` | Ejecución en CNC |
| `done` | Flujo terminado |
| `error` | Error general |

---

## 19. Valores sugeridos para `state`

| `state` | Significado |
|---|---|
| `idle` | En espera |
| `sent` | Comando enviado |
| `running` | Proceso corriendo |
| `done` | Proceso terminado |
| `error` | Error |
| `waiting` | Esperando respuesta |
| `ready` | Listo para continuar |

---

# Secuencia de prueba completa por terminal

Primero corre el programa:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

En otra terminal, simula el flujo completo:

```bash
echo '{"type":"status","step":"photo","state":"running","message":"Capturando foto","progress":10}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"framework_state","photo":true,"step":"photo","state":"done","message":"Foto lista","progress":25}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"status","step":"environment","state":"running","message":"Leyendo ambiente","progress":35}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"framework_state","environment":true,"step":"environment","state":"done","message":"Ambiente listo","progress":50}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"progress","step":"drawing","state":"running","message":"Generando SVG","progress":70}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"framework_state","drawing":true,"gcode":true,"step":"gcode","state":"done","message":"G-code listo","progress":85}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"progress","step":"execute","state":"running","message":"Dibujando","progress":95}' | nc -u -w1 127.0.0.1 5006
```

```bash
echo '{"type":"framework_state","executed":true,"step":"done","state":"done","message":"Dibujo terminado","progress":100}' | nc -u -w1 127.0.0.1 5006
```

---

# Node-RED sugerido

En Node-RED:

| Nodo | Configuración |
|---|---|
| `udp in` | Escuchar puerto `5005` |
| `json` | Convertir string UDP a objeto JSON |
| `switch` | Separar por `msg.payload.command` |
| `exec` o función | Ejecutar scripts del framework |
| `udp out` | Enviar respuesta a `127.0.0.1:5006` |

---

## Comandos esperados en Node-RED

| `msg.payload.command` | Acción sugerida |
|---|---|
| `capture_photo` | Ejecutar captura ESP32CAM |
| `capture_environment` | Ejecutar lectura ambiental |
| `generate_drawing` | Ejecutar generación SVG/G-code |
| `execute_drawing` | Ejecutar envío a GRBL |
| `show_status` | Enviar estado actual a OLED |

---

# Ejemplo de flujo lógico en Node-RED

## Al recibir `capture_photo`

1. `udp in` recibe el mensaje en puerto `5005`.
2. `json` convierte el texto en objeto.
3. `switch` detecta:

```text
msg.payload.command == "capture_photo"
```

4. Node-RED responde al OLED que empezó:

```json
{
  "type": "status",
  "step": "photo",
  "state": "running",
  "message": "Capturando foto",
  "progress": 10
}
```

5. Node-RED ejecuta el script de captura.
6. Si termina bien, manda:

```json
{
  "type": "framework_state",
  "photo": true,
  "step": "photo",
  "state": "done",
  "message": "Foto lista",
  "progress": 25
}
```

7. Si falla, manda:

```json
{
  "type": "status",
  "step": "photo",
  "state": "error",
  "message": "Error foto",
  "progress": 0
}
```

---

## Al recibir `capture_environment`

1. Node-RED responde:

```json
{
  "type": "status",
  "step": "environment",
  "state": "running",
  "message": "Leyendo ambiente",
  "progress": 30
}
```

2. Ejecuta el script de sensores.
3. Si termina bien:

```json
{
  "type": "framework_state",
  "environment": true,
  "step": "environment",
  "state": "done",
  "message": "Ambiente listo",
  "progress": 50
}
```

4. Si falla:

```json
{
  "type": "status",
  "step": "environment",
  "state": "error",
  "message": "Error ambiente",
  "progress": 25
}
```

---

## Al recibir `generate_drawing`

1. Node-RED responde:

```json
{
  "type": "status",
  "step": "drawing",
  "state": "running",
  "message": "Generando dibujo",
  "progress": 55
}
```

2. Ejecuta generación de SVG.
3. Puede mandar progreso intermedio:

```json
{
  "type": "progress",
  "step": "drawing",
  "state": "running",
  "message": "Procesando datos",
  "progress": 65
}
```

4. Luego manda:

```json
{
  "type": "progress",
  "step": "gcode",
  "state": "running",
  "message": "Generando G-code",
  "progress": 75
}
```

5. Si termina bien:

```json
{
  "type": "framework_state",
  "drawing": true,
  "gcode": true,
  "step": "gcode",
  "state": "done",
  "message": "G-code listo",
  "progress": 85
}
```

6. Si falla:

```json
{
  "type": "status",
  "step": "drawing",
  "state": "error",
  "message": "Error dibujo",
  "progress": 50
}
```

---

## Al recibir `execute_drawing`

1. Node-RED responde:

```json
{
  "type": "status",
  "step": "execute",
  "state": "running",
  "message": "Dibujando",
  "progress": 90
}
```

2. Ejecuta el envío de G-code a GRBL.
3. Si termina bien:

```json
{
  "type": "framework_state",
  "executed": true,
  "step": "done",
  "state": "done",
  "message": "Dibujo terminado",
  "progress": 100
}
```

4. Si falla:

```json
{
  "type": "status",
  "step": "execute",
  "state": "error",
  "message": "Error CNC",
  "progress": 85
}
```

---

## Al recibir `show_status`

Node-RED debería responder con el último estado conocido.

Ejemplo:

```json
{
  "type": "framework_state",
  "photo": true,
  "environment": true,
  "drawing": true,
  "gcode": true,
  "executed": false,
  "step": "gcode",
  "state": "ready",
  "message": "Listo para dibujar",
  "progress": 85
}
```

---

# Mensajes mínimos para primera integración

Para empezar poco a poco, Node-RED solo necesita manejar estos cinco comandos:

| Comando recibido | Respuesta mínima recomendada |
|---|---|
| `capture_photo` | `{"type":"framework_state","photo":true,"message":"Foto lista","progress":25}` |
| `capture_environment` | `{"type":"framework_state","environment":true,"message":"Ambiente listo","progress":50}` |
| `generate_drawing` | `{"type":"framework_state","drawing":true,"gcode":true,"message":"G-code listo","progress":85}` |
| `execute_drawing` | `{"type":"framework_state","executed":true,"message":"Dibujo terminado","progress":100}` |
| `show_status` | Estado actual completo |

---

# Plantilla de función para Node-RED

Esta función puede ir después de un nodo `json` y antes de un `udp out`.

Sirve solo para simular respuestas durante pruebas:

```javascript
const command = msg.payload.command;

let response = {
    type: "status",
    step: "inicio",
    state: "idle",
    message: "Comando recibido",
    progress: 0
};

if (command === "capture_photo") {
    response = {
        type: "framework_state",
        photo: true,
        step: "photo",
        state: "done",
        message: "Foto lista",
        progress: 25
    };
}

if (command === "capture_environment") {
    response = {
        type: "framework_state",
        environment: true,
        step: "environment",
        state: "done",
        message: "Ambiente listo",
        progress: 50
    };
}

if (command === "generate_drawing") {
    response = {
        type: "framework_state",
        drawing: true,
        gcode: true,
        step: "gcode",
        state: "done",
        message: "G-code listo",
        progress: 85
    };
}

if (command === "execute_drawing") {
    response = {
        type: "framework_state",
        executed: true,
        step: "done",
        state: "done",
        message: "Dibujo terminado",
        progress: 100
    };
}

if (command === "show_status") {
    response = {
        type: "framework_state",
        photo: false,
        environment: false,
        drawing: false,
        gcode: false,
        executed: false,
        step: "inicio",
        state: "idle",
        message: "Sistema en espera",
        progress: 0
    };
}

msg.payload = JSON.stringify(response);
return msg;
```

El nodo `udp out` debe mandar a:

```text
127.0.0.1:5006
```

---

# Prueba rápida de ida y vuelta

## Terminal 1: escuchar comandos de la OLED

```bash
nc -ul 5005
```

## Terminal 2: correr OLED

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

## Terminal 3: simular respuesta desde Node-RED

```bash
echo '{"type":"screen","title":"UDP","message":"Respuesta recibida"}' | nc -u -w1 127.0.0.1 5006
```

---

# Checklist de integración

- [ ] Correr `oled-udp.py`.
- [ ] Confirmar que OLED manda `hello` a `127.0.0.1:5005`.
- [ ] Confirmar que Node-RED recibe comandos.
- [ ] Confirmar que Node-RED responde a `127.0.0.1:5006`.
- [ ] Probar `capture_photo`.
- [ ] Probar `capture_environment`.
- [ ] Probar `generate_drawing`.
- [ ] Probar `execute_drawing`.
- [ ] Probar `show_status`.
- [ ] Probar errores con `state: "error"`.
- [ ] Integrar scripts reales paso a paso.
