# Contra Espacios - OLED + UDP para Node-RED

Programa principal de interfaz local para **Contra Espacios**.

Archivo:

```text
OLED/oled-udp.py
```

Este programa usa la misma pantalla OLED y los mismos cinco botones del programa de prueba, pero agrega comunicación UDP local para integrarse con Node-RED.

El flujo general es:

```text
Botón físico -> OLED/oled-udp.py -> UDP -> Node-RED
Node-RED -> UDP -> OLED/oled-udp.py -> pantalla OLED
```

Sí, por fin los botones dejan de ser una pantomima y empiezan a hablar con el resto del sistema. La civilización avanza a 5005 puertos por segundo.

---

## Estructura sugerida

```text
OLED/
├── oled-udp.py
├── README.md
└── test/
    ├── oled-test.py
    └── README.md
```

---

## Ejecutar

Desde el directorio `OLED`:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

---

## Dependencias importantes

Estas dos líneas son necesarias para `gpiozero` en Raspberry Pi OS moderno:

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

---

## Hardware

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

### Botones

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

---

## Puertos UDP

Por defecto:

| Dirección | Puerto | Uso |
|---|---:|---|
| `127.0.0.1` | `5005` | El programa OLED envía comandos a Node-RED |
| `127.0.0.1` | `5006` | El programa OLED escucha estado enviado por Node-RED |

Ejecutar con otros puertos:

```bash
python3 oled-udp.py --udp-send-port 5005 --udp-listen-port 5006
```

---

## Mensajes que OLED envía a Node-RED

Todos los mensajes son JSON por UDP a:

```text
127.0.0.1:5005
```

### Tabla de comandos enviados

| Acción en OLED | Mensaje enviado | Qué debería hacer Node-RED |
|---|---|---|
| Abrir programa | `{"type":"hello","message":"OLED interface online","listen_port":5006}` | Registrar que la interfaz local está activa |
| Capturar foto | `{"type":"command","command":"capture_photo","label":"Capturar foto"}` | Llamar flujo de ESP32CAM o script de captura |
| Capturar ambiente | `{"type":"command","command":"capture_environment","label":"Capturar ambiente"}` | Llamar lectura ENS160 + AHT2X |
| Generar dibujo | `{"type":"command","command":"generate_drawing","label":"Generar dibujo"}` | Generar SVG y G-code |
| Ejecutar dibujo | `{"type":"command","command":"execute_drawing","label":"Ejecutar dibujo"}` | Enviar G-code a GRBL |
| Ver estado | `{"type":"command","command":"show_status","label":"Estado"}` | Responder con estado actual |
| Cerrar programa | `{"type":"bye","message":"OLED interface offline"}` | Registrar cierre de interfaz |

El programa agrega automáticamente:

```json
{
  "source": "contraespacios_oled",
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

---

## Mensajes que Node-RED puede mandar a OLED

Node-RED debe enviar JSON por UDP a:

```text
127.0.0.1:5006
```

### Tabla de mensajes recibidos

| Tipo | Ejemplo | Resultado esperado en OLED |
|---|---|---|
| `status` | `{"type":"status","step":"photo","state":"running","message":"Capturando foto","progress":20}` | Actualiza pantalla de estado |
| `progress` | `{"type":"progress","step":"drawing","state":"running","message":"Generando SVG","progress":60}` | Muestra avance |
| `framework_state` | `{"type":"framework_state","photo":true,"environment":true,"drawing":false,"gcode":false,"executed":false}` | Actualiza banderas internas |
| `screen` | `{"type":"screen","title":"FOTO","message":"Captura lista"}` | Muestra mensaje personalizado |
| `reset` | `{"type":"reset"}` | Limpia estado local |

---

## Campos reconocidos al recibir estado

| Campo | Tipo | Uso |
|---|---|---|
| `type` | texto | `status`, `progress`, `framework_state`, `screen`, `reset` |
| `step` | texto | Paso actual: `photo`, `environment`, `drawing`, `gcode`, `execute` |
| `state` | texto | Estado: `idle`, `running`, `done`, `error` |
| `message` | texto | Mensaje breve para OLED |
| `progress` | número | Porcentaje de 0 a 100 |
| `photo` o `photo_done` | booleano | Marca foto como lista |
| `environment` o `environment_done` | booleano | Marca ambiente como listo |
| `drawing` o `drawing_done` | booleano | Marca dibujo como listo |
| `gcode` o `gcode_done` | booleano | Marca G-code como listo |
| `executed` o `executed_done` | booleano | Marca ejecución como lista |
| `title` | texto | Título para mensaje tipo `screen` |

---

## Ejemplos de prueba sin Node-RED

En una terminal, correr el programa:

```bash
cd ~/Documents/GitHub/contraespacios/OLED
source .venv/bin/activate
python3 oled-udp.py
```

En otra terminal, mandar estado simulado:

```bash
echo '{"type":"status","step":"photo","state":"running","message":"Capturando foto","progress":25}' | nc -u -w1 127.0.0.1 5006
```

Marcar foto lista:

```bash
echo '{"type":"framework_state","photo":true,"message":"Foto lista","progress":100}' | nc -u -w1 127.0.0.1 5006
```

Mostrar mensaje directo:

```bash
echo '{"type":"screen","title":"PRUEBA","message":"UDP recibido"}' | nc -u -w1 127.0.0.1 5006
```

Reiniciar estado:

```bash
echo '{"type":"reset"}' | nc -u -w1 127.0.0.1 5006
```

---

## Node-RED

En Node-RED, usar:

- nodo `udp in` escuchando puerto `5005` para recibir comandos del OLED;
- nodo `json` para convertir el mensaje;
- nodo `switch` para separar por `msg.payload.command`;
- nodo `udp out` hacia `127.0.0.1:5006` para responder estado al OLED.

---

## Menú en pantalla

La pantalla de menú solo muestra las opciones. Las instrucciones de botones viven en esta documentación para evitar flickering en la OLED.

```text
> Capturar foto
  Capturar ambiente
  Generar dibujo
  Ejecutar dibujo
  Estado
  Acerca de
```

---

## Estado de esta versión

- [x] OLED funcional.
- [x] Botones funcionales.
- [x] Menú sin texto extra.
- [x] UDP de salida hacia Node-RED.
- [x] UDP de entrada desde Node-RED.
- [x] Tabla de mensajes enviados y recibidos.
- [ ] Conectar flujo real de captura de foto.
- [ ] Conectar flujo real de sensores.
- [ ] Conectar generación SVG/G-code.
- [ ] Conectar ejecución GRBL.
