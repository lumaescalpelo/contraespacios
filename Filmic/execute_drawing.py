#!/usr/bin/env python3
import argparse
import json
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
