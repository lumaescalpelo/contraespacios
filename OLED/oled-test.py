#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contra Espacios - OLED + 5 botones - prueba de menú

Programa de prueba para Raspberry Pi.

OLED I2C:
  SDA -> GPIO2
  SCL -> GPIO3

Botones:
  GPIO17 -> arriba / anterior
  GPIO27 -> abajo / siguiente
  GPIO22 -> seleccionar
  GPIO23 -> volver
  GPIO24 -> acción / estado

Suposición de cableado:
  Cada botón conecta el GPIO a GND al presionarse.
  Por eso se usa pull_up=True.

Instalación recomendada:
  sudo apt install -y python3-pip python3-venv i2c-tools
  pip install gpiozero luma.oled pillow

Ejecutar:
  python3 contra_espacios_menu_oled_botones.py

Salir:
  Ctrl+C
"""

from __future__ import annotations

import signal
import time
from dataclasses import dataclass

from gpiozero import Button


# ---------------------------------------------------------------------
# Configuración de pines
# ---------------------------------------------------------------------

PIN_UP = 17
PIN_DOWN = 27
PIN_SELECT = 22
PIN_BACK = 23
PIN_ACTION = 24

OLED_I2C_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64


# ---------------------------------------------------------------------
# Estado del programa
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


# ---------------------------------------------------------------------
# OLED
# ---------------------------------------------------------------------

class Display:
    def __init__(self):
        self.available = False
        self.device = None
        self.font = None

        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            from PIL import ImageFont

            serial = i2c(port=1, address=OLED_I2C_ADDRESS)
            self.device = ssd1306(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
            self.font = ImageFont.load_default()
            self.available = True
        except Exception as exc:
            print("OLED no disponible, usando consola.")
            print(f"Detalle: {exc}")

    def show(self, lines: list[str]) -> None:
        lines = [str(line) for line in lines]

        if not self.available:
            print("\033c", end="")
            print("\n".join(lines))
            return

        from PIL import Image, ImageDraw

        image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
        draw = ImageDraw.Draw(image)

        y = 0
        for line in lines[:7]:
            draw.text((0, y), line[:21], font=self.font, fill=255)
            y += 9

        self.device.display(image)


display = Display()


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
    ])


def show_menu() -> None:
    visible_count = 4
    start = max(0, min(menu_index - 1, len(MENU_ITEMS) - visible_count))
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
    lines.append("SEL ok  BACK salir")

    display.show(lines)


def show_status() -> None:
    display.show([
        "ESTADO",
        f"Foto: {'OK' if state.photo_done else '--'}",
        f"Amb:  {'OK' if state.environment_done else '--'}",
        f"SVG:  {'OK' if state.drawing_done else '--'}",
        f"Gcode:{'OK' if state.gcode_done else '--'}",
        f"Draw: {'OK' if state.executed_done else '--'}",
        state.last_message[:21],
    ])


def show_about() -> None:
    display.show([
        "ACERCA DE",
        "Contra Espacios",
        "Sistema portatil",
        "para traducir",
        "ambiente en",
        "dibujo sobre",
        "cine 16mm",
    ])


def show_action(title: str, message: str) -> None:
    display.show([
        title[:21],
        "",
        message[:21],
        "",
        "Prueba sin",
        "accion real.",
        "BACK volver",
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
# Botones
# ---------------------------------------------------------------------

def go_up() -> None:
    global menu_index, current_screen

    if current_screen != "menu":
        current_screen = "menu"
        render()
        return

    menu_index = (menu_index - 1) % len(MENU_ITEMS)
    render()


def go_down() -> None:
    global menu_index, current_screen

    if current_screen != "menu":
        current_screen = "menu"
        render()
        return

    menu_index = (menu_index + 1) % len(MENU_ITEMS)
    render()


def select() -> None:
    global current_screen

    if current_screen == "splash":
        current_screen = "menu"
        render()
        return

    if current_screen == "menu":
        select_current_item()
    else:
        current_screen = "menu"
        render()


def back() -> None:
    global current_screen

    if current_screen == "splash":
        return

    current_screen = "menu"
    render()


def quick_action() -> None:
    """
    Botón 5.
    En esta versión de prueba muestra el estado.
    Más adelante puede usarse como pausa, confirmar, repetir o emergencia lógica.
    """
    global current_screen
    current_screen = "status"
    show_status()


def setup_buttons() -> list[Button]:
    buttons = [
        Button(PIN_UP, pull_up=True, bounce_time=0.12),
        Button(PIN_DOWN, pull_up=True, bounce_time=0.12),
        Button(PIN_SELECT, pull_up=True, bounce_time=0.12),
        Button(PIN_BACK, pull_up=True, bounce_time=0.12),
        Button(PIN_ACTION, pull_up=True, bounce_time=0.12),
    ]

    buttons[0].when_pressed = go_up
    buttons[1].when_pressed = go_down
    buttons[2].when_pressed = select
    buttons[3].when_pressed = back
    buttons[4].when_pressed = quick_action

    return buttons


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def stop_program(signum=None, frame=None) -> None:
    global running
    running = False
    display.show([
        "CONTRA ESPACIOS",
        "",
        "Saliendo...",
        "",
        "Prueba terminada",
    ])
    time.sleep(0.5)


def main() -> None:
    global current_screen

    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)

    buttons = setup_buttons()

    current_screen = "splash"
    render()

    time.sleep(2.5)
    current_screen = "menu"
    render()

    while running:
        time.sleep(0.1)


if __name__ == "__main__":
    main()
