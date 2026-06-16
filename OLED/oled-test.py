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
  Esta versión permite probar varios drivers/modelos de OLED.

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
# Drivers de pantalla
# ---------------------------------------------------------------------

class LumaOLED:
    """
    Control por luma.oled.

    Esta ruta permite probar modelos como ssd1306, sh1106 y sh1107 sin reescribir
    todo el programa cada vez que una OLED decide fingir que es otra OLED.
    """

    def __init__(
        self,
        driver: str,
        bus: int,
        address: int,
        width: int,
        height: int,
        rotate: int,
    ):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306, sh1106, sh1107

        serial = i2c(port=bus, address=address)

        if driver == "ssd1306":
            self.device = ssd1306(serial, width=width, height=height, rotate=rotate)
        elif driver == "sh1106":
            self.device = sh1106(serial, width=width, height=height, rotate=rotate)
        elif driver == "sh1107":
            self.device = sh1107(serial, width=width, height=height, rotate=rotate)
        else:
            raise ValueError(f"Driver luma no soportado: {driver}")

    def display_image(self, image: Image.Image) -> None:
        self.device.display(image.convert("1"))

    def cleanup(self) -> None:
        try:
            self.device.clear()
        except Exception:
            pass


class DirectPageOLED:
    """
    Driver directo por páginas para controladores compatibles con comandos tipo SSD1306/SH1106.

    Útil para probar:
    - ssd1306-direct
    - sh1106-direct
    - sh1107-direct

    Si solo aparecen líneas 8, 9 y 10 abajo, el mapeo de páginas no coincide con
    la pantalla real. En ese caso conviene probar otro driver, no seguir moviendo
    offsets como si eso fuera terapia.
    """

    def __init__(
        self,
        bus: int,
        address: int,
        width: int,
        height: int,
        controller: str,
        column_offset: int,
        page_offset: int,
        rotate_180: bool,
        contrast: int,
        multiplex: int,
    ):
        from smbus2 import SMBus

        self.SMBus = SMBus
        self.bus_number = bus
        self.address = address
        self.width = width
        self.height = height
        self.pages = height // 8
        self.controller = controller
        self.column_offset = column_offset
        self.page_offset = page_offset
        self.rotate_180 = rotate_180
        self.contrast = max(0, min(255, int(contrast)))
        self.multiplex = multiplex
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
        block_size = 8
        for i in range(0, len(data), block_size):
            self.bus.write_i2c_block_data(
                self.address,
                0x40,
                [b & 0xFF for b in data[i:i + block_size]],
            )

    def init_display(self) -> None:
        self.command(0xAE)        # Display OFF
        self.command(0xD5, 0x80)  # Clock divide
        self.command(0xA8, self.multiplex)  # Multiplex
        self.command(0xD3, 0x00)  # Display offset
        self.command(0x40)        # Start line

        if self.controller in ("ssd1306", "sh1107"):
            # Charge pump / DC-DC.
            if self.controller == "ssd1306":
                self.command(0x8D, 0x14)
            else:
                self.command(0xAD, 0x8B)

        if self.rotate_180:
            self.command(0xA0)
            self.command(0xC0)
        else:
            self.command(0xA1)
            self.command(0xC8)

        self.command(0xDA, 0x12)
        self.command(0x81, self.contrast)
        self.command(0xD9, 0xF1 if self.controller == "ssd1306" else 0x1F)
        self.command(0xDB, 0x40 if self.controller == "ssd1306" else 0x35)
        self.command(0xA4)
        self.command(0xA6)
        self.command(0xAF)
        self.clear_all_memory()

    def set_raw_page(self, raw_page: int) -> None:
        col = self.column_offset
        self.command(0xB0 + raw_page)
        self.command(0x00 + (col & 0x0F))
        self.command(0x10 + ((col >> 4) & 0x0F))

    def clear_all_memory(self) -> None:
        blank = [0x00] * self.width
        for page in range(16):
            try:
                self.set_raw_page(page)
                self.data_block(blank)
            except Exception:
                pass

    def display_image_once(self, image: Image.Image) -> None:
        image = image.convert("1")
        if self.rotate_180:
            image = image.transpose(Image.ROTATE_180)

        self.clear_all_memory()

        pixels = image.load()

        for page in range(self.pages):
            self.set_raw_page(self.page_offset + page)
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

    def display_image(self, image: Image.Image, retries: int = 3) -> None:
        last_error = None
        for attempt in range(retries):
            try:
                self.display_image_once(image)
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
            self.clear_all_memory()
        except Exception:
            pass


class Display:
    def __init__(
        self,
        driver: str,
        address: int,
        bus: int,
        width: int,
        height: int,
        column_offset: int,
        page_offset: int,
        rotate: int,
        rotate_180: bool,
        contrast: int,
        top_margin: int,
        left_margin: int,
        multiplex: int,
    ):
        self.driver = driver
        self.address = address
        self.bus = bus
        self.width = width
        self.height = height
        self.top_margin = top_margin
        self.left_margin = left_margin
        self.font = ImageFont.load_default()

        if driver in ("ssd1306", "sh1106", "sh1107"):
            self.device = LumaOLED(
                driver=driver,
                bus=bus,
                address=address,
                width=width,
                height=height,
                rotate=rotate,
            )
        elif driver in ("ssd1306-direct", "sh1106-direct", "sh1107-direct"):
            controller = driver.replace("-direct", "")
            self.device = DirectPageOLED(
                bus=bus,
                address=address,
                width=width,
                height=height,
                controller=controller,
                column_offset=column_offset,
                page_offset=page_offset,
                rotate_180=rotate_180,
                contrast=contrast,
                multiplex=multiplex,
            )
        else:
            raise ValueError(f"Driver no soportado: {driver}")

    def make_image(self, lines: list[str]) -> Image.Image:
        lines = [str(line) for line in lines]
        image = Image.new("1", (self.width, self.height))
        draw = ImageDraw.Draw(image)

        x = self.left_margin
        y = self.top_margin
        line_height = 9

        for line in lines[:10]:
            draw.text((x, y), line[:21], font=self.font, fill=255)
            y += line_height

        return image

    def show(self, lines: list[str]) -> None:
        image = self.make_image(lines)
        self.device.display_image(image)

    def cleanup(self) -> None:
        self.device.cleanup()


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
        "--driver",
        default="ssd1306",
        choices=[
            "ssd1306",
            "sh1106",
            "sh1107",
            "ssd1306-direct",
            "sh1106-direct",
            "sh1107-direct",
        ],
        help="Driver/modelo de OLED. Default: ssd1306",
    )
    parser.add_argument("--address", default="0x3C", help="Dirección I2C. Default: 0x3C")
    parser.add_argument("--bus", default=1, type=int, help="Bus I2C. Default: 1")
    parser.add_argument("--width", default=128, type=int, help="Ancho OLED. Default: 128")
    parser.add_argument("--height", default=96, type=int, help="Alto OLED. Default: 96")
    parser.add_argument("--column-offset", default=0, type=int, help="Offset de columna para drivers directos.")
    parser.add_argument("--page-offset", default=0, type=int, help="Offset de página para drivers directos.")
    parser.add_argument("--top-margin", default=0, type=int, help="Margen superior en pixeles.")
    parser.add_argument("--left-margin", default=0, type=int, help="Margen izquierdo en pixeles.")
    parser.add_argument("--rotate", default=0, type=int, choices=[0, 1, 2, 3], help="Rotación luma.")
    parser.add_argument("--rotate-180", action="store_true", help="Rotación 180 para drivers directos.")
    parser.add_argument("--contrast", default=0x7F, type=lambda x: int(x, 0), help="Contraste para drivers directos.")
    parser.add_argument("--multiplex", default=0x5F, type=lambda x: int(x, 0), help="Multiplex para drivers directos. 0x5F=96px, 0x7F=128px.")
    parser.add_argument("--screen-test", action="store_true", help="Muestra pantalla de prueba.")

    return parser.parse_args()


def main() -> None:
    global current_screen, display

    args = parse_args()
    address = int(args.address, 16) if isinstance(args.address, str) else args.address

    display = Display(
        driver=args.driver,
        address=address,
        bus=args.bus,
        width=args.width,
        height=args.height,
        column_offset=args.column_offset,
        page_offset=args.page_offset,
        rotate=args.rotate,
        rotate_180=args.rotate_180,
        contrast=args.contrast,
        top_margin=args.top_margin,
        left_margin=args.left_margin,
        multiplex=args.multiplex,
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

    try:
        display.cleanup()
    except Exception:
        pass


if __name__ == "__main__":
    main()
