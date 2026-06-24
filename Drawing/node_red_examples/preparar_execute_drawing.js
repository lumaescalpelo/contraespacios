const p = msg.payload || {};
const sessionId = p.session_id || p.active_session || flow.get("active_session") || "S01";

flow.set("active_session", sessionId);
flow.set("execution_busy", true);
flow.set("execution_done", false);

msg.session_id = sessionId;
msg.payload = [
  "--session", sessionId,
  "--data-root", "/home/pi/data",
  "--homing",
  "--set-work-zero"
].join(" ");

return msg;
