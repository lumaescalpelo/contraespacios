const p = msg.payload || {};
const sessionId = p.session_id || p.active_session || flow.get("active_session") || "S01";
flow.set("active_session", sessionId);
msg.session_id = sessionId;
msg.payload = [
  "--session", sessionId,
  "--data-root", "/home/pi/data",
  "--film-width-mm", "30",
  "--film-height-mm", "32"
].join(" ");
return msg;
