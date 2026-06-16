#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contra Espacios - oled-test.py

Prueba de pantalla OLED I2C + 5 botones para Raspberry Pi.

Forma normal:

  cd ~/Documents/GitHub/contraespacios/OLED
  source .venv/bin/activate
  python3 oled-test.py

Esta versión usa el enfoque que funcionó en la pantalla:
  - No escribe solo 96 px de memoria.
  - Dibuja en una memoria interna completa de 128 px de alto.
  - Después manda las 16 páginas completas al SH1107.
  - Permite mover el contenido dentro de esa RAM con --ram-y-offset.

Esto es necesario porque muchas OLED SH1107 128x96 usan una RAM interna
de 128x128, aunque el panel visible sea de 128x96. Si solo se escriben 12 páginas,
la pantalla puede mostrar líneas partidas, saltos, espacios en blanco y basura.

Botones de izquierda a derecha, empezando en pin físico 11:
  Botón 1: pin físico 11 / GPIO17 -> Arriba / anterior
  Botón 2: pin físico 13 / GPIO27 -> Abajo / siguiente
  Botón 3: pin físico 15 / GPIO22 -> Seleccionar
  Botón 4: pin físico 16 / GPIO23 -> Volver
  Botón 5: pin físico 18 / GPIO24 -> Estado
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

VISIBLE_WIDTH = 128
VISIBLE_HEIGHT = 96

# RAM interna típica del SH1107: 128 x 128.
RAM_WIDTH = 128
RAM_HEIGHT = 128

# Este valor funcionó correctamente al ejecutar el programa normal.
# No moverlo salvo que se esté recalibrando otra pantalla.
DEFAULT_RAM_Y_OFFSET = 64

# Margen izquierdo para evitar que se corte el primer pixel de las letras.
# Si LINEA se ve como _INEA, este margen es necesario.
DEFAULT_LEFT_MARGIN = 2

# Margen superior mínimo para aprovechar la pantalla desde arriba.
DEFAULT_TOP_MARGIN = 0


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
# Driver SH1107 usando RAM completa 128x128
# ---------------------------------------------------------------------

class SH1107FullRAM:
    """
    Driver directo SH1107 usando framebuffer interno completo 128x128.

    En vez de escribir solo 12 páginas visibles, escribe las 16 páginas.
    Esto evita que la pantalla mezcle páginas viejas con nuevas o que la ventana
    visible muestre solo líneas inferiores del texto.
    """

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
        self.command(0xAE)                  # Display OFF
        self.command(0xD5, 0x50)            # Clock divide
        self.command(0xA8, 0x7F)            # Multiplex 128 RAM lines
        self.command(0xD3, self.display_offset)
        self.command(0x40 | (self.start_line & 0x3F))

        self.command(0xAD, 0x8B)            # DC-DC SH1107

        self.command(self.segment_remap)    # 0xA0 o 0xA1
        self.command(self.com_scan)         # 0xC0 o 0xC8

        self.command(0xDA, 0x12)            # COM pins
        self.command(0x81, self.contrast)   # Contrast
        self.command(0xD9, 0x1F)            # Pre-charge
        self.command(0xDB, 0x35)            # VCOM
        self.command(0xA4)                  # Resume RAM
        self.command(0xA6)                  # Normal
        self.command(0xAF)                  # Display ON
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
        """
        Inserta la imagen visible 128x96 dentro de la RAM 128x128.
        Si ram_y_offset pasa de 127, se envuelve con módulo 128.
        """
        visible_image = visible_image.convert("1")
        ram_image = Image.new("1", (self.ram_width, self.ram_height))

        offset = self.ram_y_offset % self.ram_height

        # Pegado con wrap vertical.
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
    """
    Vista de menú optimizada para OLED 128x96.

    Se quitaron:
    - título CONTRA ESPACIOS,
    - texto Menu principal,
    - renglón vacío.

    Así caben todas las opciones y el selector no queda oculto al final.
    """
    lines = []

    for i, item in enumerate(MENU_ITEMS):
        prefix = ">" if i == menu_index else " "
        lines.append(f"{prefix} {item}")

    lines.append("")
    lines.append("B1/B2 mover")
    lines.append("B3 ok B4 atras")
    lines.append("B5 estado")

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


def show_calibrate_y() -> None:
    """
    Pantalla de calibración:
    dibuja marcas cada 8 pixeles. Sirve para ver qué zona real del framebuffer
    aparece en el panel.
    """
    image = Image.new("1", (VISIBLE_WIDTH, VISIBLE_HEIGHT))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for y in range(0, VISIBLE_HEIGHT, 8):
        draw.line((0, y, 127, y), fill=255)
        draw.text((2, y), f"Y{y:02d}", font=font, fill=255)

    display.device.display_image(image)


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
    elif current_screen == "calibrate-y":
        show_calibrate_y()
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

    parser.add_argument("--address", default="0x3C", help="Dirección I2C. Default: 0x3C")
    parser.add_argument("--bus", default=1, type=int, help="Bus I2C. Default: 1")

    parser.add_argument(
        "--ram-y-offset",
        default=DEFAULT_RAM_Y_OFFSET,
        type=int,
        help="Posición vertical del contenido dentro de la RAM 128x128. Default: 64",
    )
    parser.add_argument("--column-offset", default=0, type=int, help="Offset de columna.")
    parser.add_argument("--top-margin", default=DEFAULT_TOP_MARGIN, type=int, help="Margen superior del texto. Default: 0")
    parser.add_argument("--left-margin", default=DEFAULT_LEFT_MARGIN, type=int, help="Margen izquierdo del texto. Default: 2")

    parser.add_argument("--contrast", default=0x7F, type=lambda x: int(x, 0), help="Contraste.")
    parser.add_argument("--start-line", default=0, type=int, help="Start line SH1107.")
    parser.add_argument("--display-offset", default=0, type=int, help="Display offset SH1107.")
    parser.add_argument("--segment-remap", default=0xA1, type=lambda x: int(x, 0), help="Segment remap.")
    parser.add_argument("--com-scan", default=0xC8, type=lambda x: int(x, 0), help="COM scan.")

    parser.add_argument("--screen-test", action="store_true", help="Muestra pantalla de prueba.")
    parser.add_argument("--calibrate-y", action="store_true", help="Muestra marcas Y cada 8 pixeles.")

    return parser.parse_args()


def main() -> None:
    global current_screen, display

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

    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)

    buttons = setup_buttons()

    if args.calibrate_y:
        current_screen = "calibrate-y"
        render()
    elif args.screen_test:
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
