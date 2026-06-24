#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports


def emit(**data):
    print(json.dumps(data, ensure_ascii=False), flush=True)


def session_output_dir(data_root, session_id):
    return Path(data_root).expanduser() / "sessions" / session_id / "output"


def default_gcode_path(data_root, session_id):
    return session_output_dir(data_root, session_id) / "drawing.gcode"


def default_calibration_path(data_root):
    return Path(data_root).expanduser() / "machine" / "calibration.json"


def find_grbl_port():
    candidates = []

    for port in list_ports.comports():
        dev = port.device
        text = " ".join([
            str(port.device),
            str(port.description),
            str(port.manufacturer),
        ]).lower()

        if "arduino" in text or "ch340" in text or "usb serial" in text:
            candidates.append(dev)
        elif dev.startswith("/dev/ttyACM") or dev.startswith("/dev/ttyUSB"):
            candidates.append(dev)

    if candidates:
        return sorted(candidates)[0]

    for prefix in ("/dev/ttyACM", "/dev/ttyUSB"):
        found = sorted(Path("/dev").glob(Path(prefix + "*").name))
        if found:
            return str(found[0])

    raise FileNotFoundError("No encontré puerto serial para GRBL.")


def clean_gcode_line(line):
    line = line.strip()
    if not line:
        return ""

    if line.startswith("(") and line.endswith(")"):
        return ""

    out = []
    in_comment = False

    for ch in line:
        if ch == "(":
            in_comment = True
            continue
        if ch == ")":
            in_comment = False
            continue
        if in_comment:
            continue
        if ch == ";":
            break
        out.append(ch)

    return "".join(out).strip()


def load_gcode_lines(path):
    raw = Path(path).read_text(encoding="utf-8").splitlines()
    return [line for line in (clean_gcode_line(x) for x in raw) if line]


def save_json(path, data):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_status(line):
    status = {
        "raw": line,
        "state": "",
        "mpos": None,
        "wpos": None,
        "pins": set(),
    }

    if not (line.startswith("<") and line.endswith(">")):
        return status

    parts = line[1:-1].split("|")
    if parts:
        status["state"] = parts[0]

    for part in parts[1:]:
        if part.startswith("MPos:"):
            status["mpos"] = parse_position(part[5:])
        elif part.startswith("WPos:"):
            status["wpos"] = parse_position(part[5:])
        elif part.startswith("Pn:"):
            status["pins"] = set(part[3:])

    return status


def parse_position(text):
    try:
        vals = [float(x) for x in text.split(",")]
    except ValueError:
        return None

    while len(vals) < 3:
        vals.append(0.0)

    return {"x": vals[0], "y": vals[1], "z": vals[2]}


def read_status(ser, timeout=2.0):
    ser.write(b"?")
    ser.flush()

    deadline = time.time() + float(timeout)
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode("utf-8", errors="replace").strip()
        if line.startswith("<") and line.endswith(">"):
            return parse_status(line)

    raise TimeoutError("GRBL no respondió estado con ?.")


def wait_idle(ser, timeout=20.0):
    deadline = time.time() + float(timeout)
    last = None

    while time.time() < deadline:
        status = read_status(ser, timeout=2.0)
        last = status
        if status["state"] == "Idle":
            return status
        time.sleep(0.08)

    raw = last["raw"] if last else "sin estado"
    raise TimeoutError(f"GRBL no llegó a Idle. Último estado: {raw}")


def read_until_response(ser, timeout=60.0):
    deadline = time.time() + float(timeout)
    seen = []

    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue

        seen.append(line)
        low = line.lower()

        if low == "ok" or low.startswith("error") or low.startswith("alarm"):
            return line, seen

    raise TimeoutError("GRBL no respondió dentro del tiempo esperado.")


def send_command(ser, command, timeout=60.0):
    ser.write((command.strip() + "\n").encode("ascii"))
    ser.flush()

    response, seen = read_until_response(ser, timeout=timeout)
    low = response.lower()

    if low.startswith("error") or low.startswith("alarm"):
        raise RuntimeError(f"GRBL respondió {response} al comando: {command}")

    return response, seen


def send_and_wait_idle(ser, command, timeout=30.0):
    response, seen = send_command(ser, command, timeout=timeout)
    status = wait_idle(ser, timeout=timeout)
    return response, seen, status


def wait_for_startup(ser, timeout=4.0):
    deadline = time.time() + float(timeout)
    startup = []

    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            startup.append(line)
            if "Grbl" in line:
                break

    return startup


def stream_gcode(ser, lines, session_id):
    total = max(1, len(lines))

    for idx, line in enumerate(lines, start=1):
        send_command(ser, line, timeout=30.0)
        progress = int(round((idx / total) * 100))

        emit(
            ok=True,
            type="execute_progress",
            session_id=session_id,
            step="execute",
            state="running",
            progress=progress,
            line=idx,
            total_lines=total,
            message=f"Dibujando {progress}%",
        )


AXIS_WORD_RE = re.compile(r"([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")


def gcode_bounds(lines):
    absolute = True
    x = 0.0
    y = 0.0
    bounds = {
        "min_x": None,
        "max_x": None,
        "min_y": None,
        "max_y": None,
    }

    def include(px, py):
        if bounds["min_x"] is None:
            bounds["min_x"] = bounds["max_x"] = px
            bounds["min_y"] = bounds["max_y"] = py
            return
        bounds["min_x"] = min(bounds["min_x"], px)
        bounds["max_x"] = max(bounds["max_x"], px)
        bounds["min_y"] = min(bounds["min_y"], py)
        bounds["max_y"] = max(bounds["max_y"], py)

    for line in lines:
        words = {m.group(1): float(m.group(2)) for m in AXIS_WORD_RE.finditer(line.upper())}
        upper = line.upper()

        if "G90" in upper:
            absolute = True
        if "G91" in upper:
            absolute = False

        if not ("X" in words or "Y" in words):
            continue

        if absolute:
            if "X" in words:
                x = words["X"]
            if "Y" in words:
                y = words["Y"]
        else:
            x += words.get("X", 0.0)
            y += words.get("Y", 0.0)

        include(x, y)

    return bounds


def validate_gcode_bounds(lines, width_mm, height_mm, margin_mm=0.0):
    bounds = gcode_bounds(lines)
    if bounds["min_x"] is None:
        return bounds

    min_x = bounds["min_x"]
    max_x = bounds["max_x"]
    min_y = bounds["min_y"]
    max_y = bounds["max_y"]

    errors = []
    if min_x < -margin_mm:
        errors.append(f"X mínimo {min_x:.3f} < 0")
    if max_x > width_mm + margin_mm:
        errors.append(f"X máximo {max_x:.3f} > {width_mm:.3f}")
    if min_y < -margin_mm:
        errors.append(f"Y mínimo {min_y:.3f} < 0")
    if max_y > height_mm + margin_mm:
        errors.append(f"Y máximo {max_y:.3f} > {height_mm:.3f}")

    if errors:
        raise ValueError("G-code fuera del área calibrada: " + "; ".join(errors))

    return bounds


def scan_axis_until_limit(ser, axis, direction, args):
    axis = axis.upper()
    if axis not in ("X", "Y"):
        raise ValueError(f"Eje no soportado para calibración: {axis}")

    sign = 1.0 if int(direction) >= 0 else -1.0
    step = abs(float(args.calibration_step_mm)) * sign
    max_mm = float(args.calibration_max_x_mm if axis == "X" else args.calibration_max_y_mm)
    feed = float(args.calibration_feed_mm_min)
    total = 0.0

    send_command(ser, "G91", timeout=5.0)

    while abs(total) < max_mm:
        send_and_wait_idle(ser, f"G0 {axis}{step:.4f} F{feed:.4f}", timeout=10.0)
        total += step

        status = read_status(ser)
        if axis in status["pins"]:
            travel = abs(total)
            backoff = -sign * abs(float(args.calibration_backoff_mm))
            send_and_wait_idle(ser, f"G0 {axis}{backoff:.4f} F{feed:.4f}", timeout=10.0)
            send_command(ser, "G90", timeout=5.0)
            return travel, status

    send_command(ser, "G90", timeout=5.0)
    raise RuntimeError(f"No se encontró límite {axis} después de {max_mm:.1f} mm.")


def calibrate_area(ser, args):
    if not args.homing:
        raise ValueError("--calibrate-area requiere --homing.")

    calibration_file = Path(args.calibration_file).expanduser() if args.calibration_file else default_calibration_path(args.data_root)

    emit(ok=True, type="execute_progress", session_id=args.session, step="calibrate", state="homing", progress=3, message="Home para calibrar X")
    send_command(ser, "$H", timeout=args.homing_timeout)
    send_and_wait_idle(ser, "G10 L20 P1 X0 Y0", timeout=5.0)

    emit(ok=True, type="execute_progress", session_id=args.session, step="calibrate", state="running", progress=8, message="Buscando límite X opuesto")
    width, x_status = scan_axis_until_limit(ser, "X", args.calibrate_x_dir, args)

    emit(ok=True, type="execute_progress", session_id=args.session, step="calibrate", state="homing", progress=15, message="Home para calibrar Y")
    send_command(ser, "$H", timeout=args.homing_timeout)
    send_and_wait_idle(ser, "G10 L20 P1 X0 Y0", timeout=5.0)

    emit(ok=True, type="execute_progress", session_id=args.session, step="calibrate", state="running", progress=20, message="Buscando límite Y opuesto")
    height, y_status = scan_axis_until_limit(ser, "Y", args.calibrate_y_dir, args)

    emit(ok=True, type="execute_progress", session_id=args.session, step="calibrate", state="homing", progress=28, message="Regresando a home")
    send_command(ser, "$H", timeout=args.homing_timeout)
    send_and_wait_idle(ser, "G10 L20 P1 X0 Y0", timeout=5.0)

    calibration = {
        "ok": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session_id": args.session,
        "home_corner": args.home_corner,
        "x_scan_direction": int(args.calibrate_x_dir),
        "y_scan_direction": int(args.calibrate_y_dir),
        "usable_width_mm": round(width, 4),
        "usable_height_mm": round(height, 4),
        "backoff_mm": float(args.calibration_backoff_mm),
        "step_mm": float(args.calibration_step_mm),
        "x_limit_status": x_status["raw"],
        "y_limit_status": y_status["raw"],
        "calibration_file": str(calibration_file),
    }

    save_json(calibration_file, calibration)
    emit(
        ok=True,
        type="execute_progress",
        session_id=args.session,
        step="calibrate",
        state="done",
        progress=30,
        message=f"Área {width:.1f} x {height:.1f} mm",
        calibration=calibration,
    )

    return calibration


def run(args):
    gcode_path = Path(args.gcode).expanduser() if args.gcode else default_gcode_path(args.data_root, args.session)

    if not gcode_path.exists():
        raise FileNotFoundError(f"No existe el G-code: {gcode_path}")

    lines = load_gcode_lines(gcode_path)
    if not lines:
        raise ValueError(f"El G-code no tiene comandos ejecutables: {gcode_path}")

    port = args.port or find_grbl_port()

    emit(
        ok=True,
        type="execute_progress",
        session_id=args.session,
        step="execute",
        state="connecting",
        progress=0,
        message=f"Conectando {port}",
        gcode=str(gcode_path),
    )

    with serial.Serial(port, args.baud, timeout=0.2) as ser:
        time.sleep(args.startup_delay)
        ser.reset_input_buffer()
        ser.write(b"\r\n\r\n")
        ser.flush()
        startup = wait_for_startup(ser, timeout=3.0)

        if args.unlock:
            emit(ok=True, type="execute_progress", session_id=args.session, step="execute", state="unlocking", progress=1, message="Desbloqueando")
            send_command(ser, "$X", timeout=5.0)

        if args.homing:
            emit(ok=True, type="execute_progress", session_id=args.session, step="execute", state="homing", progress=3, message="Homing")
            send_command(ser, "$H", timeout=args.homing_timeout)

        calibration = None
        if args.calibrate_area:
            calibration = calibrate_area(ser, args)

        width = float(args.work_width_mm)
        height = float(args.work_height_mm)
        if calibration:
            width = float(calibration["usable_width_mm"])
            height = float(calibration["usable_height_mm"])

        if args.validate_bounds and width > 0 and height > 0:
            bounds = validate_gcode_bounds(lines, width, height, margin_mm=args.bounds_margin_mm)
            emit(
                ok=True,
                type="execute_progress",
                session_id=args.session,
                step="validate",
                state="done",
                progress=32,
                message="G-code dentro del área",
                bounds=bounds,
                work_area_mm={"width": width, "height": height},
            )

        if args.set_work_zero:
            emit(ok=True, type="execute_progress", session_id=args.session, step="execute", state="zeroing", progress=5, message="Cero de trabajo")
            send_command(ser, "G10 L20 P1 X0 Y0", timeout=5.0)

        emit(ok=True, type="execute_progress", session_id=args.session, step="execute", state="running", progress=6, message="Iniciando dibujo")
        stream_gcode(ser, lines, args.session)

    return {
        "ok": True,
        "type": "execute_result",
        "session_id": args.session,
        "step": "execute",
        "state": "done",
        "progress": 100,
        "message": "Dibujo ejecutado",
        "gcode": str(gcode_path),
        "port": port,
        "lines_sent": len(lines),
        "startup": startup,
        "calibration": calibration,
        "execution_done": True,
        "drawing_executed": True,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Ejecuta un drawing.gcode ya generado por Drawing.")
    p.add_argument("--session", required=True)
    p.add_argument("--data-root", default="/home/pi/data")
    p.add_argument("--gcode", default="")
    p.add_argument("--port", default="")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--startup-delay", type=float, default=2.0)
    p.add_argument("--homing", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--homing-timeout", type=float, default=60.0)
    p.add_argument("--set-work-zero", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--unlock", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--calibrate-area", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--calibration-file", default="")
    p.add_argument("--calibration-step-mm", type=float, default=1.0)
    p.add_argument("--calibration-backoff-mm", type=float, default=2.0)
    p.add_argument("--calibration-feed-mm-min", type=float, default=100.0)
    p.add_argument("--calibration-max-x-mm", type=float, default=200.0)
    p.add_argument("--calibration-max-y-mm", type=float, default=200.0)
    p.add_argument("--calibrate-x-dir", type=int, choices=(-1, 1), default=1)
    p.add_argument("--calibrate-y-dir", type=int, choices=(-1, 1), default=1)
    p.add_argument("--home-corner", default="top_left")
    p.add_argument("--work-width-mm", type=float, default=0.0)
    p.add_argument("--work-height-mm", type=float, default=0.0)
    p.add_argument("--validate-bounds", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--bounds-margin-mm", type=float, default=0.2)
    return p.parse_args()


def main():
    args = parse_args()

    try:
        result = run(args)
        emit(**result)
        return 0
    except Exception as exc:
        emit(
            ok=False,
            type="execute_result",
            session_id=getattr(args, "session", None),
            step="execute",
            state="error",
            progress=0,
            message=str(exc),
            error=str(exc),
            execution_done=False,
            drawing_executed=False,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
