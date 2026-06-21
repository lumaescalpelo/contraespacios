// Function node después de exec.
// Configurar con 2 salidas:
// salida 1 -> debug / siguiente proceso
// salida 2 -> udp out 127.0.0.1:5006

let data;

try {
    data = typeof msg.payload === "string"
        ? JSON.parse(msg.payload)
        : msg.payload;
} catch (err) {
    const oledError = {
        payload: JSON.stringify({
            type: "status",
            session_id: msg.session_id || flow.get("active_session") || "S01",
            step: "drawing",
            state: "error",
            message: "Error JSON dibujo",
            progress: 60
        }),
        ip: "127.0.0.1",
        host: "127.0.0.1",
        port: 5006
    };

    return [msg, oledError];
}

const sessionId =
    data.session_id ||
    msg.session_id ||
    flow.get("active_session") ||
    "S01";

const dataOut = {
    ...msg,
    payload: data
};

if (data.ok === true) {
    flow.set("drawing_done", true);
    flow.set("session_has_drawing", true);

    const oledOk = {
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
    };

    node.status({
        fill: "green",
        shape: "dot",
        text: `${sessionId} dibujo OK`
    });

    return [dataOut, oledOk];
}

flow.set("drawing_done", false);

const oledError = {
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
};

node.status({
    fill: "red",
    shape: "ring",
    text: data.message || "Error dibujo"
});

return [dataOut, oledError];
