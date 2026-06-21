let data;
try {
  data = typeof msg.payload === "string" ? JSON.parse(msg.payload) : msg.payload;
} catch (err) {
  return [msg, {
    payload: JSON.stringify({
      type: "status",
      step: "drawing",
      state: "error",
      message: "Error JSON dibujo",
      progress: 60
    }),
    ip: "127.0.0.1",
    host: "127.0.0.1",
    port: 5006
  }];
}

const sessionId = data.session_id || msg.session_id || flow.get("active_session") || "S01";
const dataOut = { ...msg, payload: data };

if (data.ok === true) {
  flow.set("drawing_done", true);
  flow.set("session_has_drawing", true);
  return [dataOut, {
    payload: JSON.stringify({
      type: "framework_state",
      session_id: sessionId,
      drawing: true,
      drawing_done: true,
      session_has_drawing: true,
      step: "drawing",
      state: "done",
      message: "Dibujo generado",
      progress: 75
    }),
    ip: "127.0.0.1",
    host: "127.0.0.1",
    port: 5006
  }];
}

return [dataOut, {
  payload: JSON.stringify({
    type: "status",
    session_id: sessionId,
    step: "drawing",
    state: "error",
    message: data.message || "Error dibujo",
    progress: 60
  }),
  ip: "127.0.0.1",
  host: "127.0.0.1",
  port: 5006
}];
