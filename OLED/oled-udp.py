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
    current_step: str = "inicio"
    current_state: str = "idle"
    last_message: str = "Sistema iniciado"
    progress: int = 0
    last_update: str = ""


MENU_ITEMS = [
    ("Capturar foto", "capture_photo"),
    ("Capturar ambiente", "capture_environment"),
    ("Generar dibujo", "generate_drawing"),
    ("Ejecutar dibujo", "execute_drawing"),
    ("Estado", "show_status"),
    ("Acerca de", "show_about"),
]

state = FrameworkState()
menu_index = 0
current_screen = "splash"
running = True
events: "queue.Queue[tuple[str, object]]" = queue.Queue()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


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

            try:
                payload = json.loads(data.decode("utf-8"))
                events.put(("udp", payload))
            except Exception as exc:
                events.put(("udp_error", f"UDP inválido: {exc}"))


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
    lines = []
    for i, (label, _command) in enumerate(MENU_ITEMS):
        prefix = ">" if i == menu_index else " "
        lines.append(f"{prefix} {label}")
    display.show(lines)


def show_status() -> None:
    display.show([
        "ESTADO FRAMEWORK",
        f"Paso: {state.current_step[:14]}",
        f"Modo: {state.current_state[:14]}",
        f"Foto:  {'OK' if state.photo_done else '--'}",
        f"Amb:   {'OK' if state.environment_done else '--'}",
        f"Gcode: {'OK' if state.gcode_done else '--'}",
        f"Draw:  {'OK' if state.executed_done else '--'}",
        f"Prog:  {state.progress}%",
        state.last_message[:21],
    ])


def show_about() -> None:
    display.show([
        "ACERCA DE",
        "Contra Espacios",
        "Interfaz local",
        "OLED + botones",
        "envia comandos",
        "UDP a Node-RED",
        "y muestra estado",
        "del framework.",
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
        "",
        message[:21],
        "",
        state.current_step[:21],
        state.current_state[:21],
        f"Prog: {state.progress}%",
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
    elif current_screen == "about":
        show_about()
    elif current_screen == "screen-test":
        show_screen_test()
    else:
        show_menu()


def send_command(command: str, label: str) -> None:
    if udp is None:
        return

    udp.send({
        "type": "command",
        "command": command,
        "label": label,
    })


def select_current_item() -> None:
    global current_screen
    label, command = MENU_ITEMS[menu_index]

    if command == "show_status":
        current_screen = "status"
        show_status()
        send_command(command, label)
        return

    if command == "show_about":
        current_screen = "about"
        show_about()
        return

    state.current_step = command
    state.current_state = "sent"
    state.last_message = f"Enviado: {label}"
    state.last_update = now_iso()

    current_screen = "action"
    show_action(label, "Enviado a Node-RED")
    send_command(command, label)


def update_state_from_udp(payload: dict) -> None:
    global current_screen

    msg_type = payload.get("type", "status")

    if msg_type in ("status", "framework_state", "progress"):
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

        # Alias cortos para que Node-RED pueda mandar mensajes más cómodos.
        if "photo" in payload:
            state.photo_done = bool(payload["photo"])
        if "environment" in payload:
            state.environment_done = bool(payload["environment"])
        if "drawing" in payload:
            state.drawing_done = bool(payload["drawing"])
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


def handle_event(event: str) -> None:
    global menu_index, current_screen

    if event == "up":
        if current_screen != "menu":
            current_screen = "menu"
        else:
            menu_index = (menu_index - 1) % len(MENU_ITEMS)
        render()
    elif event == "down":
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
        else:
            current_screen = "menu"
            render()
    elif event == "back":
        if current_screen != "splash":
            current_screen = "menu"
            render()
    elif event == "status":
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

    parser.add_argument("--udp-send-host", default="127.0.0.1")
    parser.add_argument("--udp-send-port", default=5005, type=int)
    parser.add_argument("--udp-listen-host", default="127.0.0.1")
    parser.add_argument("--udp-listen-port", default=5006, type=int)

    return parser.parse_args()


def main() -> None:
    global current_screen, display, udp
    args = parse_args()
    address = int(args.address, 16) if isinstance(args.address, str) else args.address

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
                state.last_message = str(payload)
                current_screen = "status"
                show_status()
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
