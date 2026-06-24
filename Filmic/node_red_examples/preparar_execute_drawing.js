const p = msg.payload || {};
const sessionId = p.session_id || p.active_session || flow.get("active_session") || "S01";

flow.set("active_session", sessionId);
flow.set("execution_busy", true);
flow.set("execution_done", false);
flow.set("drawing_executed", false);

msg.session_id = sessionId;
msg.payload = [
  "--session", sessionId,
  "--data-root", "/home/pi/data",
  "--homing",
  "--calibrate-area",
  "--calibrate-x-dir", "1",
  "--calibrate-y-dir", "-1",
  "--calibration-step-mm", "4",
  "--calibration-fine-step-mm", "1",
  "--calibration-backoff-mm", "6",
  "--calibration-feed-mm-min", "350",
  "--calibration-fine-feed-mm-min", "180",
  "--fit-gcode-to-area",
  "--fit-margin-mm", "1",
  "--fit-mode", "uniform",
  "--set-work-zero",
  "--unlock"
].join(" ");

return msg;
