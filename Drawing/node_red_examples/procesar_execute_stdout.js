// Conecta este Function a stdout del nodo exec de execute_drawing.py.
// El exec debe entregar salida "mientras el comando se ejecuta".

const text = String(msg.payload || "");
const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);

let last = null;
for (const line of lines) {
  try {
    last = JSON.parse(line);
  } catch (err) {
    node.warn("Linea no JSON desde execute_drawing.py: " + line);
  }
}

if (!last) {
  return null;
}

const sessionId = last.session_id || msg.session_id || flow.get("active_session") || "S01";

if (last.ok === true && last.state === "done") {
  flow.set("execution_busy", false);
  flow.set("execution_done", true);
  flow.set("drawing_executed", true);
}

if (last.ok === false || last.state === "error") {
  flow.set("execution_busy", false);
  flow.set("execution_done", false);
}

msg.payload = JSON.stringify({
  type: "framework_state",
  session_id: sessionId,
  step: "execute",
  state: last.state || "running",
  progress: last.progress || 0,
  message: last.message || "Ejecutando",

  execution_busy: flow.get("execution_busy") || false,
  execution_done: flow.get("execution_done") || false,
  drawing_executed: flow.get("drawing_executed") || false,

  gcode: last.gcode
});

msg.ip = "127.0.0.1";
msg.host = "127.0.0.1";
msg.port = 5006;

return msg;
