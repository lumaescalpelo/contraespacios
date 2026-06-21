// Function node antes de exec.
// Configura el exec con:
// /home/pi/Documents/GitHub/contraespacios/Drawing/.venv/bin/python /home/pi/Documents/GitHub/contraespacios/Drawing/generate_drawing.py
// y activa "Append msg.payload".

const p = msg.payload || {};

const sessionId =
    p.session_id ||
    p.active_session ||
    flow.get("active_session") ||
    "S01";

flow.set("active_session", sessionId);

msg.session_id = sessionId;

msg.payload = [
    "--session", sessionId,
    "--data-root", "/home/pi/data",
    "--film-width-mm", "16",
    "--film-height-mm", "43"
].join(" ");

node.status({
    fill: "blue",
    shape: "dot",
    text: `Generando ${sessionId}`
});

return msg;
