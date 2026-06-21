"""
Configuración base del motor de dibujo de Contra Espacios.

La salida principal es SVG en milímetros. La primera zona de dibujo está pensada
para película de 16 mm x 43 mm, pero puede cambiarse por argumentos de terminal.
"""

from dataclasses import dataclass


@dataclass
class DrawingConfig:
    film_width_mm: float = 16.0
    film_height_mm: float = 43.0
    margin_mm: float = 0.7

    image_process_height_px: int = 640

    max_photos: int = 12
    max_paths: int = 80
    max_points_per_path: int = 220
    min_points_per_path: int = 8

    blur_size: int = 5
    canny_low: int = 60
    canny_high: int = 150
    contour_simplify_ratio: float = 0.006

    preview_height_px: int = 1200
    preview_line_width_px: int = 2

    stroke_width_mm: float = 0.10
    base_seed: int = 1337
    algorithm_name: str = "contraespacios_svg_v1"


DEFAULT_CONFIG = DrawingConfig()
