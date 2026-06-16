#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contra Espacios - oled-test.py

Prueba de pantalla OLED I2C + 5 botones para Raspberry Pi.

Pantalla:
  OLED I2C en GPIO2 / GPIO3.
  Este programa usa SH1107 128x96 por defecto, porque algunas pantallas OLED
  de 1.13" 128x96 se ven con ruido o texto roto si se controlan como SSD1306.

Botones, de izquierda a derecha, empezando en pin físico 11:
  Botón 1: pin físico 11 / GPIO17 -> Arriba / anterior
  Botón 2: pin físico 13 / GPIO27 -> Abajo / siguiente
  Botón 3: pin físico 15 / GPIO22 -> Seleccionar
  Botón 4: pin físico 16 / GPIO23 -> Volver
  Botón 5: pin físico 18 / GPIO24 -> Estado / acción rápida

Este es un programa de prueba:
  - No captura fotos reales.
  - No lee sensores reales.
  - No genera SVG real.
  - No genera G-code real.
  - No mueve la CNC.

Solo prueba:
  - OLED.
  - Botones.
  - Presentación.
  - Menú.
  - Estados simulados.
"""

from __future__ import annotations

import argparse
import queue
import signal
import sys
import time
from dataclasses import dataclass
from typing import Optional

from gpiozero import Button


# ---------------------------------------------------------------------
# Pines
# ---------------------------------------------------------------------

# Botones físicos de izquierda a derecha, empezando en pin físico 11.
PIN_BUTTON_1 = 17  # Físico 11
PIN_BUTTON_2 = 27  # Físico 13
PIN_BUTTON_3 = 22  # Físico 15
PIN_BUTTON_4 = 23  # Físico 16
PIN_BUTTON_5 = 24  # Físico 18

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
    """
    Usa LGPIOFactory de forma explícita.

    En Raspberry Pi OS moderno, gpiozero necesita un backend GPIO funcional.
    Sin lgpio puede caer al backend NativeFactory/sysfs, que suele romperse.
    """
    try:
        from gpiozero.pins.lgpio import LGPIOFactory
        return LGPIOFactory()
    except Exception as exc:
        print("No se pudo cargar LGPIOFactory.")
        print(f"Detalle: {exc}")
        print()
        print("Instala soporte GPIO con:")
        print("  sudo apt install -y python3-lgpio python3-gpiozero")
        print("  python3 -m venv --system-site-packages .venv")
        print()
        raise


# ---------------------------------------------------------------------
# OLED
# ---------------------------------------------------------------------

class Display:
    """
    Control de OLED.

    Importante:
    - No se escribe a la pantalla desde callbacks de botones.
    - Los callbacks solo meten eventos a una cola.
    - El loop principal procesa eventos y redibuja.

    Esto evita errores I2C cuando se presionan botones rápido o cuando el callback
    de gpiozero intenta dibujar desde otro hilo. Sí, los hilos otra vez arruinando
    la paz social.
    """

    def __init__(
        self,
        driver: str = "sh1107",
        address: int = OLED_I2C_ADDRESS,
        width: int = OLED_WIDTH,
        height: int = OLED_HEIGHT,
        rotate: int = 0,
        console: bool = False,
    ):
        self.driver = driver
        self.address = address
        self.width = width
        self.height = height
        self.rotate = rotate
        self.console = console
        self.available = False
        self.device = None
        self.font = None

        if self.console:
            return

        self.init_device()

    def init_device(self) -> None:
        try:
            from luma.core.interface.serial import i2c
            from PIL import ImageFont

            serial = i2c(port=1, address=self.address)

            if self.driver == "sh1107":
                from luma.oled.device import sh1107
                self.device = sh1107(
                    serial,
                    width=self.width,
                    height=self.height,
                    rotate=self.rotate,
                )

            elif self.driver == "ssd1306":
                from luma.oled.device import ssd1306
                self.device = ssd1306(
                    serial,
                    width=self.width,
                    height=self.height,
                    rotate=self.rotate,
                )

            elif self.driver == "sh1106":
                from luma.oled.device import sh1106
                self.device = sh1106(
                    serial,
                    width=self.width,
                    height=self.height,
                    rotate=self.rotate,
                )

            else:
                raise ValueError(f"Driver no soportado: {self.driver}")

            self.font = ImageFont.load_default()
            self.available = True

        except Exception as exc:
            self.available = False
            print("OLED no disponible. Usando salida por consola.")
            print(f"Driver solicitado: {self.driver}")
            print(f"Detalle: {exc}")

    def show(self, lines: list[str]) -> None:
        lines = [str(line) for line in lines]

        if self.console or not self.available:
            print("\033c", end="")
            print("\n".join(lines))
            return

        try:
            from PIL import Image, ImageDraw

            image = Image.new("1", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            y = 0
            line_height = 9

            for line in lines[:10]:
                draw.text((0, y), line[:21], font=self.font, fill=255)
                y += line_height

            self.device.display(image)

        except OSError as exc:
            # Si el bus I2C se cae, no matamos el programa.
            # Marcamos OLED como no disponible y seguimos en consola.
            self.available = False
            print("Error I2C al escribir OLED. Cambio temporal a consola.")
            print(f"Detalle: {exc}")
            print("\n".join(lines))

        except Exception as exc:
            self.available = False
            print("Error al escribir OLED. Cambio temporal a consola.")
            print(f"Detalle: {exc}")
            print("\n".join(lines))


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


def render() -> None:
    if current_screen == "splash":
        show_splash()
    elif current_screen == "menu":
        show_menu()
    elif current_screen == "status":
        show_status()
    elif current_screen == "about":
        show_about()
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
        Button(PIN_BUTTON_1, pull_up=True, bounce_time=0.18, pin_factory=pin_factory),
        Button(PIN_BUTTON_2, pull_up=True, bounce_time=0.18, pin_factory=pin_factory),
        Button(PIN_BUTTON_3, pull_up=True, bounce_time=0.18, pin_factory=pin_factory),
        Button(PIN_BUTTON_4, pull_up=True, bounce_time=0.18, pin_factory=pin_factory),
        Button(PIN_BUTTON_5, pull_up=True, bounce_time=0.18, pin_factory=pin_factory),
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
        "--display",
        default="sh1107",
        choices=["sh1107", "ssd1306", "sh1106", "console"],
        help="Driver de pantalla. Default: sh1107",
    )
    parser.add_argument(
        "--rotate",
        default=0,
        type=int,
        choices=[0, 1, 2, 3],
        help="Rotación de pantalla para luma.oled.",
    )
    parser.add_argument(
        "--address",
        default="0x3C",
        help="Dirección I2C. Default: 0x3C",
    )
    return parser.parse_args()


def main() -> None:
    global current_screen, display

    args = parse_args()
    address = int(args.address, 16) if isinstance(args.address, str) else args.address

    display = Display(
        driver="sh1107" if args.display == "console" else args.display,
        address=address,
        width=OLED_WIDTH,
        height=OLED_HEIGHT,
        rotate=args.rotate,
        console=(args.display == "console"),
    )

    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)

    buttons = setup_buttons()

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
