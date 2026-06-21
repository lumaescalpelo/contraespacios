"""
Configuración base del motor de dibujo de Contra Espacios.
Versión v2 orientada a mayor semejanza con las fotos.
"""

from dataclasses import dataclass


@dataclass
class DrawingConfig:
    # Dimensiones físicas iniciales.
    film_width_mm: float = 16.0
    film_height_mm: float = 43.0
    margin_mm: float = 0.7

    # Procesamiento de imagen.
    image_process_height_px: int = 720
    max_photos: int = 12

    # Contornos.
    max_contours: int = 120
    max_points_per_contour: int = 280
    min_points_per_contour: int = 8
    blur_size: int = 5
    canny_low: int = 45
    canny_high: int = 120
    contour_simplify_ratio: float = 0.004

    # Raster / escaneo tonal.
    base_scanlines: int = 56
    max_scanlines: int = 120
    samples_per_scanline: int = 180
    base_amplitude_mm: float = 0.32
    max_amplitude_mm: float = 0.85
    tonal_gain: float = 0.85
    edge_gain: float = 0.90

    # SVG/preview.
    preview_height_px: int = 1200
    preview_line_width_px: int = 2
    stroke_width_mm: float = 0.10

    algorithm_name: str = "contraespacios_svg_v2_photo"


DEFAULT_CONFIG = DrawingConfig()
