#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contra Espacios - oled-test.py

Prueba de pantalla OLED I2C + 5 botones para Raspberry Pi.

Forma normal de ejecución:

  cd ~/Documents/GitHub/contraespacios/OLED
  source .venv/bin/activate
  python3 oled-test.py

Pantalla:
  OLED I2C en GPIO2 / GPIO3.
  Control directo SH1107 128x96.
  Default: page_offset 0 para que el texto arranque arriba.

Botones, de izquierda a derecha, empezando en pin físico 11:
  Botón 1: pin físico 11 / GPIO17 -> Arriba / anterior
  Botón 2: pin físico 13 / GPIO27 -> Abajo / siguiente
  Botón 3: pin físico 15 / GPIO22 -> Seleccionar
  Botón 4: pin físico 16 / GPIO23 -> Volver
  Botón 5: pin físico 18 / GPIO24 -> Estado

Este es un programa de prueba:
  - No captura fotos reales.
  - No lee sensores reales.
  - No genera SVG real.
  - No genera G-code real.
  - No mueve la CNC.
"""

from __future__ import annotations

import argparse
import queue
import signal
import time
from dataclasses import dataclass
from typing import Optional

from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------
# Pines
# ---------------------------------------------------------------------

PIN_BUTTON_1 = 17  # Pin físico 11
PIN_BUTTON_2 = 27  # Pin físico 13
PIN_BUTTON_3 = 22  # Pin físico 15
PIN_BUTTON_4 = 23  # Pin físico 16
PIN_BUTTON_5 = 24  # Pin físico 18

OLED_I2C_BUS = 1
OLED_I2C_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 96

# Si el título sale a media pantalla, el offset era demasiado alto.
# Default corregido: escribir desde página 0.
DEFAULT_PAGE_OFFSET = 0
DEFAULT_COLUMN_OFFSET = 0


# ---------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------

@dataclass
class ProjectState:
    photo_done: bool = False
    environment_done: bool = False
    drawing_done: bool = False
    gcode_done: bool = False
    executed_done: bool = False
    last_message: str = "Sistema iniciado"


MENU_ITEMS = [
    "Capturar foto",
    "Capturar ambiente",
    "Generar dibujo",
    "Ejecutar dibujo",
    "Estado",
    "Acerca de",
]

state = ProjectState()
menu_index = 0
current_screen = "splash"
running = True
events: "queue.Queue[str]" = queue.Queue()


# ---------------------------------------------------------------------
# GPIO
# ---------------------------------------------------------------------

def get_pin_factory():
    """Usa LGPIOFactory de forma explícita en Raspberry Pi OS moderno."""
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


# ---------------------------------------------------------------------
# Driver directo SH1107
# ---------------------------------------------------------------------

class SH1107Direct:
    """
    Driver mínimo directo para OLED SH1107 128x96 por I2C.

    Esta versión:
    - dibuja desde la parte superior,
    - limpia la RAM completa antes de cada pantalla,
    - no cae a consola si falla I2C,
    - intenta reconectar la OLED automáticamente.
    """

    def __init__(
        self,
        bus: int = OLED_I2C_BUS,
        address: int = OLED_I2C_ADDRESS,
        width: int = OLED_WIDTH,
        height: int = OLED_HEIGHT,
        column_offset: int = DEFAULT_COLUMN_OFFSET,
        page_offset: int = DEFAULT_PAGE_OFFSET,
        rotate_180: bool = False,
        contrast: int = 0x7F,
    ):
        from smbus2 import SMBus

        self.SMBus = SMBus
        self.bus_number = bus
        self.address = address
        self.width = width
        self.height = height
        self.pages = height // 8
        self.column_offset = column_offset
        self.page_offset = page_offset
        self.rotate_180 = rotate_180
        self.contrast = max(0, min(255, int(contrast)))
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
        time.sleep(0.15)
        self.connect()

    def command(self, *cmds: int) -> None:
        for cmd in cmds:
            self.bus.write_byte_data(self.address, 0x00, cmd & 0xFF)

    def data_block(self, data: list[int]) -> None:
        # Bloques pequeños para evitar errores I2C.
        block_size = 8
        for i in range(0, len(data), block_size):
            self.bus.write_i2c_block_data(
                self.address,
                0x40,
                [b & 0xFF for b in data[i:i + block_size]],
            )

    def init_display(self) -> None:
        self.command(0xAE)        # Display OFF
        self.command(0xD5, 0x50)  # Clock divide
        self.command(0xA8, 0x5F)  # Multiplex ratio: 96 - 1
        self.command(0xD3, 0x00)  # Display offset
        self.command(0x40)        # Display start line 0

        # DC-DC / charge pump SH1107.
        self.command(0xAD, 0x8B)

        if self.rotate_180:
            self.command(0xA0)
            self.command(0xC0)
        else:
            self.command(0xA1)
            self.command(0xC8)

        self.command(0xDA, 0x12)          # COM pins
        self.command(0x81, self.contrast) # Contrast
        self.command(0xD9, 0x1F)          # Pre-charge
        self.command(0xDB, 0x35)          # VCOM deselect
        self.command(0xA4)                # Resume from RAM
        self.command(0xA6)                # Normal display
        self.command(0xAF)                # Display ON
        self.clear_all_memory()

    def clear_all_memory(self) -> None:
        blank = [0x00] * self.width

        # SH1107 puede tener 16 páginas internas aunque el módulo visible sea 96 px.
        for page in range(16):
            self.set_raw_page(page)
            self.data_block(blank)

    def set_raw_page(self, raw_page: int) -> None:
        col = self.column_offset
        self.command(0xB0 + raw_page)
        self.command(0x00 + (col & 0x0F))
        self.command(0x10 + ((col >> 4) & 0x0F))

    def set_page(self, page: int) -> None:
        raw_page = self.page_offset + page
        self.set_raw_page(raw_page)

    def display_image_once(self, image: Image.Image) -> None:
        image = image.convert("1")

        if self.rotate_180:
            image = image.transpose(Image.ROTATE_180)

        # Limpieza total para no dejar texto viejo abajo.
        self.clear_all_memory()

        pixels = image.load()

        for page in range(self.pages):
            self.set_page(page)
            data = []
            y0 = page * 8

            for x in range(self.width):
                byte = 0
                for bit in range(8):
                    y = y0 + bit
                    if y < self.height and pixels[x, y] != 0:
                        byte |= (1 << bit)
                data.append(byte)

            self.data_block(data)

    def display_image(self, image: Image.Image, retries: int = 3) -> bool:
        last_error = None

        for attempt in range(retries):
            try:
                self.display_image_once(image)
                return True
            except OSError as exc:
                last_error = exc
                print(f"Advertencia I2C OLED: {exc}. Reintentando conexión ({attempt + 1}/{retries})...")
                try:
                    self.reconnect()
                except Exception as reconnect_exc:
                    last_error = reconnect_exc
                    print(f"No se pudo reconectar OLED: {reconnect_exc}")
                    time.sleep(0.2)
            except Exception as exc:
                last_error = exc
                print(f"Error OLED: {exc}. Reintentando ({attempt + 1}/{retries})...")
                try:
                    self.reconnect()
                except Exception as reconnect_exc:
                    last_error = reconnect_exc
                    print(f"No se pudo reconectar OLED: {reconnect_exc}")
                    time.sleep(0.2)

        print(f"No se pudo actualizar OLED después de {retries} intentos. Último error: {last_error}")
        return False


# ---------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------

class Display:
    def __init__(
        self,
        address: int = OLED_I2C_ADDRESS,
        bus: int = OLED_I2C_BUS,
        width: int = OLED_WIDTH,
        height: int = OLED_HEIGHT,
        column_offset: int = DEFAULT_COLUMN_OFFSET,
        page_offset: int = DEFAULT_PAGE_OFFSET,
        rotate_180: bool = False,
        contrast: int = 0x7F,
        top_margin: int = 0,
        left_margin: int = 0,
    ):
        self.address = address
        self.bus = bus
        self.width = width
        self.height = height
        self.top_margin = top_margin
        self.left_margin = left_margin
        self.device = SH1107Direct(
            bus=bus,
            address=address,
            width=width,
            height=height,
            column_offset=column_offset,
            page_offset=page_offset,
            rotate_180=rotate_180,
            contrast=contrast,
        )
        self.font = ImageFont.load_default()

    def show(self, lines: list[str]) -> None:
        lines = [str(line) for line in lines]

        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)

        # Layout superior, no centrado.
        x = self.left_margin
        y = self.top_margin
        line_height = 9

        for line in lines[:10]:
            draw.text((x, y), line[:21], font=self.font, fill=255)
            y += line_height

        self.device.display_image(image)


display: Optional[Display] = None


# ---------------------------------------------------------------------
# Pantallas
# ---------------------------------------------------------------------

def show_splash() -> None:
    display.show([
        "CONTRA ESPACIOS",
        "",
        "Dibujo 16mm",
        "Ambiente + CNC",
        "",
        "Amaranta",
        "Chikiframe",
        "",
        "OLED + botones",
    ])


def show_menu() -> None:
    visible_count = 5
    start = max(0, min(menu_index - 2, len(MENU_ITEMS) - visible_count))
    visible = MENU_ITEMS[start:start + visible_count]

    lines = [
        "CONTRA ESPACIOS",
        "Menu principal",
        "",
    ]

    for i, item in enumerate(visible, start=start):
        prefix = ">" if i == menu_index else " "
        lines.append(f"{prefix} {item}")

    lines.append("")
    lines.append("B3 OK  B4 volver")
    display.show(lines)


def show_status() -> None:
    display.show([
        "ESTADO",
        f"Foto:  {'OK' if state.photo_done else '--'}",
        f"Amb:   {'OK' if state.environment_done else '--'}",
        f"SVG:   {'OK' if state.drawing_done else '--'}",
        f"Gcode: {'OK' if state.gcode_done else '--'}",
        f"Draw:  {'OK' if state.executed_done else '--'}",
        "",
        state.last_message[:21],
        "",
        "B4 volver",
    ])


def show_about() -> None:
    display.show([
        "ACERCA DE",
        "Contra Espacios",
        "",
        "Sistema portatil",
        "que traduce",
        "ambiente + foto",
        "en dibujo sobre",
        "cine 16mm",
        "",
        "B4 volver",
    ])


def show_action(title: str, message: str) -> None:
    display.show([
        title[:21],
        "",
        message[:21],
        "",
        "Esta prueba aun",
        "no ejecuta una",
        "accion real.",
        "",
        "B4 volver",
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


# ---------------------------------------------------------------------
# Acciones simuladas
# ---------------------------------------------------------------------

def simulate_photo() -> None:
    state.photo_done = True
    state.last_message = "Foto simulada OK"
    show_action("1 FOTO", "Captura simulada")


def simulate_environment() -> None:
    state.environment_done = True
    state.last_message = "Ambiente sim OK"
    show_action("2 AMBIENTE", "Lectura simulada")


def simulate_generate() -> None:
    if not state.photo_done or not state.environment_done:
        state.last_message = "Falta foto/amb"
        show_action("3 GENERAR", "Falta foto/amb")
        return

    state.drawing_done = True
    state.gcode_done = True
    state.last_message = "SVG/Gcode sim OK"
    show_action("3 GENERAR", "SVG y Gcode OK")


def simulate_execute() -> None:
    if not state.gcode_done:
        state.last_message = "Falta Gcode"
        show_action("4 DIBUJAR", "Falta Gcode")
        return

    state.executed_done = True
    state.last_message = "Dibujo sim OK"
    show_action("4 DIBUJAR", "Ejecucion OK")


def select_current_item() -> None:
    global current_screen

    item = MENU_ITEMS[menu_index]

    if item == "Capturar foto":
        current_screen = "action"
        simulate_photo()
    elif item == "Capturar ambiente":
        current_screen = "action"
        simulate_environment()
    elif item == "Generar dibujo":
        current_screen = "action"
        simulate_generate()
    elif item == "Ejecutar dibujo":
        current_screen = "action"
        simulate_execute()
    elif item == "Estado":
        current_screen = "status"
        show_status()
    elif item == "Acerca de":
        current_screen = "about"
        show_about()


# ---------------------------------------------------------------------
# Eventos de botones
# ---------------------------------------------------------------------

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


def setup_buttons() -> list[Button]:
    pin_factory = get_pin_factory()

    buttons = [
        Button(PIN_BUTTON_1, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_2, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_3, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_4, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
        Button(PIN_BUTTON_5, pull_up=True, bounce_time=0.22, pin_factory=pin_factory),
    ]

    # Los callbacks NO dibujan pantalla. Solo agregan eventos.
    buttons[0].when_pressed = lambda: events.put("up")
    buttons[1].when_pressed = lambda: events.put("down")
    buttons[2].when_pressed = lambda: events.put("select")
    buttons[3].when_pressed = lambda: events.put("back")
    buttons[4].when_pressed = lambda: events.put("status")

    return buttons


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def stop_program(signum=None, frame=None) -> None:
    global running
    running = False


def parse_args():
    parser = argparse.ArgumentParser(description="Contra Espacios OLED + botones test")
    parser.add_argument(
        "--address",
        default="0x3C",
        help="Dirección I2C. Default: 0x3C",
    )
    parser.add_argument(
        "--bus",
        default=1,
        type=int,
        help="Bus I2C. Default: 1",
    )
    parser.add_argument(
        "--column-offset",
        default=DEFAULT_COLUMN_OFFSET,
        type=int,
        help="Offset de columna. Default: 0",
    )
    parser.add_argument(
        "--page-offset",
        default=DEFAULT_PAGE_OFFSET,
        type=int,
        help="Offset de página. Default: 0",
    )
    parser.add_argument(
        "--top-margin",
        default=0,
        type=int,
        help="Margen superior del texto en pixeles. Default: 0",
    )
    parser.add_argument(
        "--left-margin",
        default=0,
        type=int,
        help="Margen izquierdo del texto en pixeles. Default: 0",
    )
    parser.add_argument(
        "--rotate-180",
        action="store_true",
        help="Rota la imagen 180 grados.",
    )
    parser.add_argument(
        "--contrast",
        default=0x7F,
        type=lambda x: int(x, 0),
        help="Contraste. Default: 0x7F",
    )
    parser.add_argument(
        "--screen-test",
        action="store_true",
        help="Muestra una pantalla de prueba de alineación.",
    )
    return parser.parse_args()


def main() -> None:
    global current_screen, display

    args = parse_args()
    address = int(args.address, 16) if isinstance(args.address, str) else args.address

    display = Display(
        address=address,
        bus=args.bus,
        width=OLED_WIDTH,
        height=OLED_HEIGHT,
        column_offset=args.column_offset,
        page_offset=args.page_offset,
        rotate_180=args.rotate_180,
        contrast=args.contrast,
        top_margin=args.top_margin,
        left_margin=args.left_margin,
    )

    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)

    buttons = setup_buttons()

    if args.screen_test:
        current_screen = "screen-test"
        render()
    else:
        current_screen = "splash"
        render()
        time.sleep(2.5)
        current_screen = "menu"
        render()

    while running:
        try:
            event = events.get(timeout=0.1)
            handle_event(event)
        except queue.Empty:
            pass

    display.show([
        "CONTRA ESPACIOS",
        "",
        "Saliendo...",
        "",
        "Prueba terminada",
    ])
    time.sleep(0.3)


if __name__ == "__main__":
    main()
