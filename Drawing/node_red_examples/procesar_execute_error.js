flow.set("execution_busy", false);
flow.set("execution_done", false);

const sessionId = msg.session_id || flow.get("active_session") || "S01";
const errorText = typeof msg.payload === "string" ? msg.payload : JSON.stringify(msg.payload);

node.warn(errorText);

msg.payload = JSON.stringify({
  type: "framework_state",
  session_id: sessionId,
  step: "execute",
  state: "error",
  progress: 0,
  message: "Error al ejecutar",
  execution_busy: false,
  execution_done: false,
  drawing_executed: false,
  detail: errorText.slice(0, 80)
});

msg.ip = "127.0.0.1";
msg.host = "127.0.0.1";
msg.port = 5006;

return msg;
