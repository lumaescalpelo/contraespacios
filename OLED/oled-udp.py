#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contra Espacios - OLED local interface

OLED I2C:
  SDA -> GPIO2
  SCL -> GPIO3

Botones de izquierda a derecha, empezando en pin físico 11:
  Botón 1: pin físico 11 / GPIO17 -> Arriba / anterior
  Botón 2: pin físico 13 / GPIO27 -> Abajo / siguiente
  Botón 3: pin físico 15 / GPIO22 -> Seleccionar
  Botón 4: pin físico 16 / GPIO23 -> Volver
  Botón 5: pin físico 18 / GPIO24 -> Estado
"""

from __future__ import annotations

import argparse
import json
import queue
import signal
import socket
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont


PIN_BUTTON_1 = 17
PIN_BUTTON_2 = 27
PIN_BUTTON_3 = 22
PIN_BUTTON_4 = 23
PIN_BUTTON_5 = 24

OLED_I2C_BUS = 1
OLED_I2C_ADDRESS = 0x3C

VISIBLE_WIDTH = 128
VISIBLE_HEIGHT = 96
RAM_WIDTH = 128
RAM_HEIGHT = 128

DEFAULT_RAM_Y_OFFSET = 64
DEFAULT_LEFT_MARGIN = 2
DEFAULT_TOP_MARGIN = 0


@dataclass
class FrameworkState:
    photo_done: bool = False
    environment_done: bool = False
    drawing_done: bool = False
    gcode_done: bool = False
    executed_done: bool = False
    photo_count: int = 0
    environment_count: int = 0
    current_step: str = "inicio"
    current_state: str = "idle"
    last_message: str = "Sistema iniciado"
    progress: int = 0
    last_update: str = ""
    active_session: str = "S01"
    session_has_drawing: bool = False
    session_total: int = 1
    session_position: int = 1


MENU_ITEMS = [
    ("Capturar foto", "capture_photo"),
    ("Capturar ambiente", "capture_environment"),
    ("Nueva sesion", "new_session"),
    ("Seleccionar sesion", "select_session"),
    ("Generar dibujo", "generate_drawing"),
    ("Ejecutar dibujo", "execute_drawing"),
    ("Estado", "show_status"),
]

state = FrameworkState()
menu_index = 0
session_select_index = 0
current_screen = "splash"
running = True
events: "queue.Queue[tuple[str, object]]" = queue.Queue()

# Se configura en main() con --data-root.
DATA_ROOT: Path = Path.home() / "Documents" / "GitHub" / "contraespacios" / "data"
STATE_FILE: Path = DATA_ROOT / "state.json"
SESSIONS_DIR: Path = DATA_ROOT / "sessions"
MAX_SESSIONS = 64


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def session_sort_key(session_id: str) -> int:
    try:
        return int(str(session_id).replace("S", ""))
    except Exception:
        return 9999


def valid_session_id(session_id: str) -> bool:
    if not isinstance(session_id, str):
        return False
    if len(session_id) != 3 or not session_id.startswith("S"):
        return False
    try:
        n = int(session_id[1:])
    except Exception:
        return False
    return 1 <= n <= MAX_SESSIONS


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def session_json_path(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"


def default_session_doc(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "status": "collecting",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "photo_count": 0,
        "environment_count": 0,
        "drawing_done": False,
        "gcode_done": False,
        "executed_done": False,
        "photos": [],
        "environment": [],
        "output": {
            "drawing_svg": None,
            "gcode": None,
            "metadata": None,
        },
    }


def read_json_file(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"No se pudo leer JSON {path}: {exc}")
    return default


def write_json_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def scan_sessions() -> list[str]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions: list[str] = []
    for item in SESSIONS_DIR.iterdir():
        if item.is_dir() and valid_session_id(item.name):
            sessions.append(item.name)
    sessions.sort(key=session_sort_key)
    return sessions


def detect_session_has_drawing(session_id: str, doc: Optional[dict] = None) -> bool:
    if doc is None:
        doc = read_json_file(session_json_path(session_id), {})
    if bool(doc.get("drawing_done")):
        return True
    output = doc.get("output", {}) if isinstance(doc.get("output", {}), dict) else {}
    for key in ("drawing_svg", "gcode", "metadata"):
        value = output.get(key)
        if value:
            return True
    out_dir = session_dir(session_id) / "output"
    if (out_dir / "drawing.svg").exists():
        return True
    if (out_dir / "dibujo.svg").exists():
        return True
    return False


def ensure_session(session_id: str) -> dict:
    if not valid_session_id(session_id):
        session_id = "S01"

    d = session_dir(session_id)
    (d / "photos").mkdir(parents=True, exist_ok=True)
    (d / "environment").mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(parents=True, exist_ok=True)

    path = session_json_path(session_id)
    if path.exists():
        doc = read_json_file(path, default_session_doc(session_id))
    else:
        doc = default_session_doc(session_id)

    doc["session_id"] = session_id
    doc.setdefault("status", "collecting")
    doc.setdefault("created_at", now_iso())
    doc["updated_at"] = now_iso()
    doc.setdefault("photo_count", 0)
    doc.setdefault("environment_count", 0)
    doc.setdefault("drawing_done", False)
    doc.setdefault("gcode_done", False)
    doc.setdefault("executed_done", False)
    doc.setdefault("photos", [])
    doc.setdefault("environment", [])
    doc.setdefault("output", {"drawing_svg": None, "gcode": None, "metadata": None})
    write_json_file(path, doc)
    return doc


def active_session_from_state_file() -> str:
    state_doc = read_json_file(STATE_FILE, {})
    session_id = state_doc.get("active_session", "S01")
    if not valid_session_id(session_id):
        session_id = "S01"
    return session_id


def write_global_state(active_session: str) -> None:
    sessions = scan_sessions()
    state_doc = read_json_file(STATE_FILE, {})
    state_doc.update({
        "active_session": active_session,
        "last_session": active_session,
        "max_sessions": MAX_SESSIONS,
        "session_count": len(sessions),
        "updated_at": now_iso(),
    })
    write_json_file(STATE_FILE, state_doc)


def refresh_session_state(session_id: Optional[str] = None) -> None:
    global session_select_index

    if session_id is None:
        session_id = state.active_session
    if not valid_session_id(session_id):
        session_id = "S01"

    doc = ensure_session(session_id)
    write_global_state(session_id)

    sessions = scan_sessions()
    if session_id not in sessions:
        sessions.append(session_id)
        sessions.sort(key=session_sort_key)

    position = sessions.index(session_id) + 1 if session_id in sessions else 1
    total = max(1, len(sessions))
    session_select_index = position - 1

    state.active_session = session_id
    state.session_total = total
    state.session_position = position
    state.session_has_drawing = detect_session_has_drawing(session_id, doc)
    state.photo_count = int(doc.get("photo_count", 0) or 0)
    state.environment_count = int(doc.get("environment_count", 0) or 0)
    state.photo_done = state.photo_count > 0
    state.environment_done = state.environment_count > 0
    state.drawing_done = bool(doc.get("drawing_done", False))
    state.gcode_done = bool(doc.get("gcode_done", False))
    state.executed_done = bool(doc.get("executed_done", False))


def update_active_session_doc() -> None:
    session_id = state.active_session
    if not valid_session_id(session_id):
        return

    doc = ensure_session(session_id)
    doc["updated_at"] = now_iso()
    doc["photo_count"] = int(state.photo_count)
    doc["environment_count"] = int(state.environment_count)
    doc["drawing_done"] = bool(state.drawing_done)
    doc["gcode_done"] = bool(state.gcode_done)
    doc["executed_done"] = bool(state.executed_done)

    if state.executed_done:
        doc["status"] = "executed"
    elif state.gcode_done:
        doc["status"] = "gcode_generated"
    elif state.drawing_done or state.session_has_drawing:
        doc["status"] = "drawing_generated"
    else:
        doc.setdefault("status", "collecting")

    write_json_file(session_json_path(session_id), doc)
    write_global_state(session_id)


def init_sessions(data_root: Path) -> None:
    global DATA_ROOT, STATE_FILE, SESSIONS_DIR
    DATA_ROOT = data_root.expanduser().resolve()
    STATE_FILE = DATA_ROOT / "state.json"
    SESSIONS_DIR = DATA_ROOT / "sessions"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    sessions = scan_sessions()
    if not sessions:
        ensure_session("S01")
        write_global_state("S01")
        refresh_session_state("S01")
        return

    active = active_session_from_state_file()
    if active not in sessions:
        active = sessions[0]
    refresh_session_state(active)


def next_available_session() -> Optional[str]:
    used = set(scan_sessions())
    for i in range(1, MAX_SESSIONS + 1):
        candidate = f"S{i:02d}"
        if candidate not in used:
            return candidate
    return None


def session_label(session_id: Optional[str] = None) -> str:
    if session_id is None:
        session_id = state.active_session
    star = "*" if state.session_has_drawing and session_id == state.active_session else ""
    return f"{session_id}{star}"


def create_new_session() -> Optional[str]:
    session_id = next_available_session()
    if session_id is None:
        return None
    ensure_session(session_id)
    refresh_session_state(session_id)
    return session_id


def select_session_by_index(index: int) -> Optional[str]:
    sessions = scan_sessions()
    if not sessions:
        ensure_session("S01")
        sessions = ["S01"]
    index = max(0, min(len(sessions) - 1, index))
    session_id = sessions[index]
    refresh_session_state(session_id)
    return session_id


def get_pin_factory():
    try:
        from gpiozero.pins.lgpio import LGPIOFactory
        return LGPIOFactory()
    except Exception as exc:
        print("ERROR: No se pudo cargar LGPIOFactory.")
        print(f"Detalle: {exc}")
        print()
        print("Instala soporte GPIO con:")
        print("  sudo apt install -y python3-lgpio python3-gpiozero")
        print("  python3 -m venv --system-site-packages .venv")
        print()
        raise


class SH1107FullRAM:
    def __init__(
        self,
        bus: int,
        address: int,
        ram_width: int,
        ram_height: int,
        visible_width: int,
        visible_height: int,
        ram_y_offset: int,
        column_offset: int,
        contrast: int,
        start_line: int,
        display_offset: int,
        segment_remap: int,
        com_scan: int,
    ):
        from smbus2 import SMBus

        self.SMBus = SMBus
        self.bus_number = bus
        self.address = address
        self.ram_width = ram_width
        self.ram_height = ram_height
        self.ram_pages = ram_height // 8
        self.visible_width = visible_width
        self.visible_height = visible_height
        self.ram_y_offset = ram_y_offset
        self.column_offset = column_offset
        self.contrast = max(0, min(255, int(contrast)))
        self.start_line = start_line & 0x7F
        self.display_offset = display_offset & 0x7F
        self.segment_remap = segment_remap
        self.com_scan = com_scan
        self.bus = None
        self.connect()

    def connect(self) -> None:
        if self.bus is not None:
            try:
                self.bus.close()
            except Exception:
                pass
        self.bus = self.SMBus(self.bus_number)
        self.init_display()

    def reconnect(self) -> None:
        time.sleep(0.2)
        self.connect()

    def command(self, *cmds: int) -> None:
        for cmd in cmds:
            self.bus.write_byte_data(self.address, 0x00, cmd & 0xFF)

    def data_block(self, data: list[int]) -> None:
        block_size = 16
        for i in range(0, len(data), block_size):
            self.bus.write_i2c_block_data(
                self.address,
                0x40,
                [b & 0xFF for b in data[i:i + block_size]],
            )

    def init_display(self) -> None:
        self.command(0xAE)
        self.command(0xD5, 0x50)
        self.command(0xA8, 0x7F)
        self.command(0xD3, self.display_offset)
        self.command(0x40 | (self.start_line & 0x3F))
        self.command(0xAD, 0x8B)
        self.command(self.segment_remap)
        self.command(self.com_scan)
        self.command(0xDA, 0x12)
        self.command(0x81, self.contrast)
        self.command(0xD9, 0x1F)
        self.command(0xDB, 0x35)
        self.command(0xA4)
        self.command(0xA6)
        self.command(0xAF)
        self.clear()

    def set_page(self, page: int) -> None:
        col = self.column_offset
        self.command(0xB0 + page)
        self.command(0x00 + (col & 0x0F))
        self.command(0x10 + ((col >> 4) & 0x0F))

    def clear(self) -> None:
        blank = [0x00] * self.ram_width
        for page in range(self.ram_pages):
            self.set_page(page)
            self.data_block(blank)

    def make_ram_image(self, visible_image: Image.Image) -> Image.Image:
        visible_image = visible_image.convert("1")
        ram_image = Image.new("1", (self.ram_width, self.ram_height))
        offset = self.ram_y_offset % self.ram_height

        remaining = self.ram_height - offset
        if remaining >= self.visible_height:
            ram_image.paste(visible_image, (0, offset))
        else:
            top_part = visible_image.crop((0, 0, self.visible_width, remaining))
            bottom_part = visible_image.crop((0, remaining, self.visible_width, self.visible_height))
            ram_image.paste(top_part, (0, offset))
            ram_image.paste(bottom_part, (0, 0))

        return ram_image

    def display_image_once(self, visible_image: Image.Image) -> None:
        ram_image = self.make_ram_image(visible_image)
        pixels = ram_image.load()

        for page in range(self.ram_pages):
            self.set_page(page)
            data = []
            y0 = page * 8

            for x in range(self.ram_width):
                byte = 0
                for bit in range(8):
                    y = y0 + bit
                    if pixels[x, y] != 0:
                        byte |= (1 << bit)
                data.append(byte)

            self.data_block(data)

    def display_image(self, visible_image: Image.Image, retries: int = 3) -> None:
        last_error = None
        for attempt in range(retries):
            try:
                self.display_image_once(visible_image)
                return
            except OSError as exc:
                last_error = exc
                print(f"Advertencia I2C OLED: {exc}. Reintentando ({attempt + 1}/{retries})...")
                try:
                    self.reconnect()
                except Exception as reconnect_exc:
                    last_error = reconnect_exc
                    print(f"No se pudo reconectar OLED: {reconnect_exc}")
                    time.sleep(0.2)
        raise RuntimeError(f"No se pudo actualizar OLED. Último error: {last_error}")

    def cleanup(self) -> None:
        try:
            self.clear()
        except Exception:
            pass


class Display:
    def __init__(
        self,
        address: int,
        bus: int,
        ram_y_offset: int,
        column_offset: int,
        contrast: int,
        top_margin: int,
        left_margin: int,
        start_line: int,
        display_offset: int,
        segment_remap: int,
        com_scan: int,
    ):
        self.visible_width = VISIBLE_WIDTH
        self.visible_height = VISIBLE_HEIGHT
        self.top_margin = top_margin
        self.left_margin = left_margin
        self.font = ImageFont.load_default()

        self.device = SH1107FullRAM(
            bus=bus,
            address=address,
            ram_width=RAM_WIDTH,
            ram_height=RAM_HEIGHT,
            visible_width=VISIBLE_WIDTH,
            visible_height=VISIBLE_HEIGHT,
            ram_y_offset=ram_y_offset,
            column_offset=column_offset,
            contrast=contrast,
            start_line=start_line,
            display_offset=display_offset,
            segment_remap=segment_remap,
            com_scan=com_scan,
        )

    def make_image(self, lines: list[str]) -> Image.Image:
        image = Image.new("1", (self.visible_width, self.visible_height))
        draw = ImageDraw.Draw(image)
        x = self.left_margin
        y = self.top_margin
        line_height = 9
        for line in [str(line) for line in lines][:10]:
            draw.text((x, y), line[:21], font=self.font, fill=255)
            y += line_height
        return image

    def show(self, lines: list[str]) -> None:
        self.device.display_image(self.make_image(lines))

    def cleanup(self) -> None:
        self.device.cleanup()


display: Optional[Display] = None


class UDPBridge:
    def __init__(self, send_host: str, send_port: int, listen_host: str, listen_port: int):
        self.send_addr = (send_host, send_port)
        self.listen_addr = (listen_host, listen_port)
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind(self.listen_addr)
        self.listen_socket.settimeout(0.2)
        self.thread = threading.Thread(target=self.listen_loop, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def send(self, payload: dict) -> None:
        payload.setdefault("source", "contraespacios_oled")
        payload.setdefault("timestamp", now_iso())
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_socket.sendto(data, self.send_addr)

    def listen_loop(self) -> None:
        while running:
            try:
                data, addr = self.listen_socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break

            raw = data.decode("utf-8", errors="replace").strip()

            try:
                payload = json.loads(raw)

                # Solo aceptamos objetos JSON.
                # Si por error Node-RED manda "[object Object]" o una lista,
                # no debe romper la pantalla ni reemplazar el estado visible.
                if isinstance(payload, dict):
                    events.put(("udp", payload))
                else:
                    print(f"UDP ignorado, JSON no es objeto: {raw[:80]}")

            except Exception as exc:
                # No mostramos esto en OLED para no tapar progreso/estado real.
                print(f"UDP inválido ignorado: {exc} | raw={raw[:80]}")


udp: Optional[UDPBridge] = None


def show_splash() -> None:
    display.show([
        "CONTRA ESPACIOS",
        "",
        "OLED + UDP",
        "Node-RED local",
        "",
        "Amaranta",
        "Chikiframe",
        "",
        "Iniciando...",
    ])


def show_menu() -> None:
    lines = [f"SES {session_label()}"]
    for i, (label, _command) in enumerate(MENU_ITEMS):
        prefix = ">" if i == menu_index else " "
        lines.append(f"{prefix} {label}")
    display.show(lines)


def short_step(step: str) -> str:
    aliases = {
        "capture_photo": "foto",
        "photo": "foto",
        "capture_environment": "ambiente",
        "environment": "ambiente",
        "generate_drawing": "dibujo",
        "drawing": "dibujo",
        "gcode": "gcode",
        "execute_drawing": "ejecutar",
        "execute": "ejecutar",
        "done": "terminado",
        "show_status": "estado",
        "inicio": "inicio",
    }
    return aliases.get(str(step), str(step))


def short_state(mode: str) -> str:
    aliases = {
        "idle": "idle",
        "sent": "sent",
        "running": "run",
        "partial": "part",
        "done": "done",
        "error": "error",
        "waiting": "wait",
        "ready": "ready",
    }
    return aliases.get(str(mode), str(mode))


def okmark(value: bool) -> str:
    return "OK" if value else "--"


def show_status() -> None:
    # Pantalla visible real: 128x96.
    # Estado compacto con sesión visible.
    step = short_step(state.current_step)
    mode = short_state(state.current_state)
    message = str(state.last_message).replace("\n", " ").strip()

    display.show([
        f"EST {state.progress:3d}% {mode[:5]}",
        f"Ses:{session_label()}",
        f"Paso:{step[:16]}",
        f"Msg:{message[:17]}",
        f"F:{state.photo_count:02d} A:{state.environment_count:02d}",
        f"Dib:{okmark(state.drawing_done)} G:{okmark(state.gcode_done)}",
        f"Ex:{okmark(state.executed_done)} {state.last_update[-8:] if state.last_update else ''}",
    ])


def show_session_created(session_id: str) -> None:
    display.show([
        "NUEVA SESION",
        f"Activa: {session_label(session_id)}",
        "",
        "Todo se guarda",
        "en esta sesion",
        "",
        "Select: menu",
    ])


def show_no_sessions_available() -> None:
    display.show([
        "SESIONES LLENAS",
        "Maximo 64",
        "No se creo",
        "nueva sesion",
        "",
        "Volver: menu",
    ])


def show_session_select() -> None:
    sessions = scan_sessions()
    if not sessions:
        ensure_session("S01")
        sessions = ["S01"]

    idx = max(0, min(session_select_index, len(sessions) - 1))
    session_id = sessions[idx]
    doc = read_json_file(session_json_path(session_id), {})
    has_drawing = detect_session_has_drawing(session_id, doc)
    star = "*" if has_drawing else ""

    display.show([
        "ELEGIR SESION",
        f"Sesion {idx + 1:02d}/{len(sessions):02d}",
        f"ID: {session_id}{star}",
        f"Fotos: {int(doc.get('photo_count', 0) or 0):02d}",
        f"Amb:   {int(doc.get('environment_count', 0) or 0):02d}",
        f"Dib: {'OK' if has_drawing else '--'}",
        "Sel: activar",
        "Back: menu",
    ])


def show_action(title: str, message: str) -> None:
    display.show([
        title[:21],
        "",
        message[:21],
        "",
        "Comando enviado",
        "por UDP local.",
        "",
        "Esperando estado...",
    ])


def show_screen_message(title: str, message: str) -> None:
    display.show([
        title[:21],
        message[:21],
        f"Ses:{session_label()}",
        f"Paso:{short_step(state.current_step)[:16]}",
        f"Modo:{short_state(state.current_state)[:16]}",
        f"Prog:{state.progress}%",
        f"F:{state.photo_count:02d} A:{state.environment_count:02d}",
        f"D:{okmark(state.drawing_done)} G:{okmark(state.gcode_done)} E:{okmark(state.executed_done)}",
    ])


def show_screen_test() -> None:
    display.show([
        "LINEA 1 ARRIBA",
        "LINEA 2",
        "LINEA 3",
        "LINEA 4",
        "LINEA 5",
        "LINEA 6",
        "LINEA 7",
        "LINEA 8",
        "LINEA 9",
        "LINEA 10",
    ])


def render() -> None:
    if current_screen == "splash":
        show_splash()
    elif current_screen == "menu":
        show_menu()
    elif current_screen == "status":
        show_status()
    elif current_screen == "session_select":
        show_session_select()
    elif current_screen == "screen-test":
        show_screen_test()
    else:
        show_menu()


def send_command(command: str, label: str, extra: Optional[dict] = None) -> None:
    if udp is None:
        return

    payload = {
        "type": "command",
        "command": command,
        "label": label,
        "session_id": state.active_session,
        "active_session": state.active_session,
        "session_has_drawing": state.session_has_drawing,
    }
    if extra:
        payload.update(extra)

    udp.send(payload)


def select_current_item() -> None:
    global current_screen, session_select_index
    label, command = MENU_ITEMS[menu_index]

    if command == "show_status":
        refresh_session_state()
        current_screen = "status"
        show_status()
        send_command(command, label)
        return

    if command == "new_session":
        new_id = create_new_session()
        if new_id is None:
            state.last_message = "No hay sesiones libres"
            state.current_step = "new_session"
            state.current_state = "error"
            state.last_update = now_iso()
            current_screen = "status"
            show_no_sessions_available()
            return

        state.current_step = "new_session"
        state.current_state = "done"
        state.last_message = f"Sesion {new_id} activa"
        state.progress = 0
        state.last_update = now_iso()
        current_screen = "session_created"
        show_session_created(new_id)
        send_command("new_session", "Nueva sesion", {"session_id": new_id, "active_session": new_id})
        return

    if command == "select_session":
        sessions = scan_sessions()
        if not sessions:
            ensure_session("S01")
            sessions = ["S01"]
        if state.active_session in sessions:
            session_select_index = sessions.index(state.active_session)
        else:
            session_select_index = 0
        current_screen = "session_select"
        show_session_select()
        return

    state.current_step = command
    state.current_state = "sent"
    state.last_message = f"Enviado: {label}"
    state.last_update = now_iso()

    current_screen = "action"
    show_action(label, f"Sesion {session_label()}")
    send_command(command, label)


def update_state_from_udp(payload: dict) -> None:
    global current_screen

    msg_type = payload.get("type", "status")

    # Compatibilidad extra:
    # Si por error o por diseño llega directo un mensaje del ESP32 ambiental
    # con type="environment", lo convertimos a estado OLED.
    # Así la OLED no depende de que Node-RED lo traduzca perfecto.
    if msg_type == "environment":
        env_state = str(payload.get("state", "running"))
        stage = str(payload.get("stage", ""))
        message = str(payload.get("message", "Ambiente"))
        progress = payload.get("progress", 40)

        has_all_values = (
            payload.get("aht_ok") is True
            and payload.get("ens_ok") is True
            and payload.get("temperature") is not None
            and payload.get("humidity") is not None
            and payload.get("aqi") is not None
            and payload.get("tvoc") is not None
            and payload.get("eco2") is not None
        )

        mapped = {
            "type": "status",
            "step": "environment",
            "state": env_state,
            "message": message,
            "progress": progress,
        }

        if stage == "complete":
            if env_state == "done" and has_all_values:
                mapped.update({
                    "type": "framework_state",
                    "environment": True,
                    "environment_done": True,
                    "state": "done",
                    "message": "Ambiente listo",
                    "progress": progress,
                })
            else:
                mapped.update({
                    "environment": False,
                    "environment_done": False,
                    "state": "error",
                    "message": message or "Lectura incompleta",
                })

        payload = mapped
        msg_type = payload.get("type", "status")

    if msg_type in ("status", "framework_state", "progress"):
        if "session_id" in payload or "active_session" in payload:
            incoming_session = str(payload.get("session_id", payload.get("active_session", state.active_session)))
            if valid_session_id(incoming_session):
                refresh_session_state(incoming_session)

        if "photo_done" in payload:
            state.photo_done = bool(payload["photo_done"])
        if "environment_done" in payload:
            state.environment_done = bool(payload["environment_done"])
        if "drawing_done" in payload:
            state.drawing_done = bool(payload["drawing_done"])
        if "gcode_done" in payload:
            state.gcode_done = bool(payload["gcode_done"])
        if "executed_done" in payload:
            state.executed_done = bool(payload["executed_done"])

        if "photo_count" in payload:
            try:
                state.photo_count = max(0, int(payload["photo_count"]))
            except Exception:
                pass
        if "environment_count" in payload:
            try:
                state.environment_count = max(0, int(payload["environment_count"]))
            except Exception:
                pass

        # Alias cortos para que Node-RED pueda mandar mensajes más cómodos.
        if "photo" in payload:
            state.photo_done = bool(payload["photo"])
        if "environment" in payload:
            state.environment_done = bool(payload["environment"])
        if "drawing" in payload:
            state.drawing_done = bool(payload["drawing"])
        if state.drawing_done:
            state.session_has_drawing = True
        if "session_has_drawing" in payload:
            state.session_has_drawing = bool(payload["session_has_drawing"])
        if "gcode" in payload:
            state.gcode_done = bool(payload["gcode"])
        if "executed" in payload:
            state.executed_done = bool(payload["executed"])

        if "step" in payload:
            state.current_step = str(payload["step"])
        if "state" in payload:
            state.current_state = str(payload["state"])
        if "message" in payload:
            state.last_message = str(payload["message"])
        if "progress" in payload:
            try:
                state.progress = max(0, min(100, int(payload["progress"])))
            except Exception:
                pass

        state.last_update = now_iso()
        update_active_session_doc()

        # Si Node-RED avisa algo, mostrar estado inmediatamente.
        current_screen = "status"
        show_status()

    elif msg_type == "screen":
        title = str(payload.get("title", "MENSAJE"))
        message = str(payload.get("message", ""))
        state.last_message = message
        state.last_update = now_iso()
        current_screen = "message"
        show_screen_message(title, message)

    elif msg_type == "reset":
        state.photo_done = False
        state.environment_done = False
        state.drawing_done = False
        state.gcode_done = False
        state.executed_done = False
        state.current_step = "inicio"
        state.current_state = "idle"
        state.last_message = "Sistema reiniciado"
        state.progress = 0
        state.last_update = now_iso()
        current_screen = "status"
        show_status()


def activate_selected_session() -> None:
    global current_screen
    sessions = scan_sessions()
    if not sessions:
        ensure_session("S01")
        sessions = ["S01"]
    idx = max(0, min(session_select_index, len(sessions) - 1))
    session_id = select_session_by_index(idx)
    if session_id is None:
        return

    state.current_step = "select_session"
    state.current_state = "done"
    state.last_message = f"Sesion {session_id} activa"
    state.last_update = now_iso()
    current_screen = "status"
    show_status()
    send_command("select_session", "Seleccionar sesion", {"session_id": session_id, "active_session": session_id})


def handle_event(event: str) -> None:
    global menu_index, current_screen, session_select_index

    if event == "up":
        if current_screen == "session_select":
            sessions = scan_sessions()
            if sessions:
                session_select_index = (session_select_index - 1) % len(sessions)
            show_session_select()
            return

        if current_screen != "menu":
            current_screen = "menu"
        else:
            menu_index = (menu_index - 1) % len(MENU_ITEMS)
        render()

    elif event == "down":
        if current_screen == "session_select":
            sessions = scan_sessions()
            if sessions:
                session_select_index = (session_select_index + 1) % len(sessions)
            show_session_select()
            return

        if current_screen != "menu":
            current_screen = "menu"
        else:
            menu_index = (menu_index + 1) % len(MENU_ITEMS)
        render()

    elif event == "select":
        if current_screen == "splash":
            current_screen = "menu"
            render()
        elif current_screen == "menu":
            select_current_item()
        elif current_screen == "session_select":
            activate_selected_session()
        else:
            current_screen = "menu"
            render()

    elif event == "back":
        if current_screen != "splash":
            current_screen = "menu"
            render()

    elif event == "status":
        refresh_session_state()
        current_screen = "status"
        show_status()
        send_command("show_status", "Estado")


def setup_buttons() -> list[Button]:
    pin_factory = get_pin_factory()
    buttons = [
        Button(PIN_BUTTON_1, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_2, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_3, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_4, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_5, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
    ]
    buttons[0].when_pressed = lambda: events.put(("button", "up"))
    buttons[1].when_pressed = lambda: events.put(("button", "down"))
    buttons[2].when_pressed = lambda: events.put(("button", "select"))
    buttons[3].when_pressed = lambda: events.put(("button", "back"))
    buttons[4].when_pressed = lambda: events.put(("button", "status"))
    return buttons


def stop_program(signum=None, frame=None) -> None:
    global running
    running = False


def parse_args():
    parser = argparse.ArgumentParser(description="Contra Espacios OLED UDP interface")
    parser.add_argument("--address", default="0x3C")
    parser.add_argument("--bus", default=1, type=int)
    parser.add_argument("--ram-y-offset", default=DEFAULT_RAM_Y_OFFSET, type=int)
    parser.add_argument("--column-offset", default=0, type=int)
    parser.add_argument("--top-margin", default=DEFAULT_TOP_MARGIN, type=int)
    parser.add_argument("--left-margin", default=DEFAULT_LEFT_MARGIN, type=int)
    parser.add_argument("--contrast", default=0x7F, type=lambda x: int(x, 0))
    parser.add_argument("--start-line", default=0, type=int)
    parser.add_argument("--display-offset", default=0, type=int)
    parser.add_argument("--segment-remap", default=0xA1, type=lambda x: int(x, 0))
    parser.add_argument("--com-scan", default=0xC8, type=lambda x: int(x, 0))
    parser.add_argument("--screen-test", action="store_true")
    parser.add_argument(
        "--data-root",
        default=str(Path.home() / "Documents" / "GitHub" / "contraespacios" / "data"),
        help="Carpeta base para state.json y sessions/",
    )

    parser.add_argument("--udp-send-host", default="127.0.0.1")
    parser.add_argument("--udp-send-port", default=5005, type=int)
    parser.add_argument("--udp-listen-host", default="127.0.0.1")
    parser.add_argument("--udp-listen-port", default=5006, type=int)

    return parser.parse_args()


def main() -> None:
    global current_screen, display, udp
    args = parse_args()
    address = int(args.address, 16) if isinstance(args.address, str) else args.address

    init_sessions(Path(args.data_root))

    display = Display(
        address=address,
        bus=args.bus,
        ram_y_offset=args.ram_y_offset,
        column_offset=args.column_offset,
        contrast=args.contrast,
        top_margin=args.top_margin,
        left_margin=args.left_margin,
        start_line=args.start_line,
        display_offset=args.display_offset,
        segment_remap=args.segment_remap,
        com_scan=args.com_scan,
    )

    udp = UDPBridge(
        send_host=args.udp_send_host,
        send_port=args.udp_send_port,
        listen_host=args.udp_listen_host,
        listen_port=args.udp_listen_port,
    )
    udp.start()

    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)
    buttons = setup_buttons()

    udp.send({
        "type": "hello",
        "message": "OLED interface online",
        "listen_port": args.udp_listen_port,
        "active_session": state.active_session,
        "session_id": state.active_session,
        "session_has_drawing": state.session_has_drawing,
        "data_root": str(DATA_ROOT),
    })

    if args.screen_test:
        current_screen = "screen-test"
        render()
    else:
        current_screen = "splash"
        render()
        time.sleep(2.0)
        current_screen = "menu"
        render()

    while running:
        try:
            kind, payload = events.get(timeout=0.1)
            if kind == "button":
                handle_event(payload)
            elif kind == "udp":
                update_state_from_udp(payload)
            elif kind == "udp_error":
                # Los UDP inválidos ya se imprimen en terminal.
                # No se muestran en OLED para no tapar el estado/progreso.
                print(str(payload))
        except queue.Empty:
            pass

    try:
        udp.send({"type": "bye", "message": "OLED interface offline"})
    except Exception:
        pass

    try:
        display.cleanup()
    except Exception:
        pass


if __name__ == "__main__":
    main()
