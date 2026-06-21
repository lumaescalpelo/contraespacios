from dataclasses import dataclass


@dataclass
class DrawingConfig:
    # V3 nace horizontal.
    film_width_mm: float = 43.0
    film_height_mm: float = 16.0
    margin_mm: float = 0.8

    image_process_height_px: int = 420
    max_photos: int = 12

    # Cuantización / masas.
    quantization_levels: int = 5
    blur_size: int = 7

    # Contornos grandes.
    max_contours: int = 14
    max_points_per_contour: int = 120
    min_points_per_contour: int = 10
    contour_simplify_ratio: float = 0.010
    min_contour_area_ratio: float = 0.0025

    # Bandas parciales tipo paisaje.
    landscape_bands: int = 7
    band_samples: int = 90
    band_dark_threshold: float = 0.50
    band_amplitude_mm: float = 0.90
    band_min_length_ratio: float = 0.08

    # Líneas internas suaves.
    internal_lines: int = 4
    internal_samples: int = 80
    internal_dark_threshold: float = 0.40
    internal_amplitude_mm: float = 0.55

    # Salidas.
    stroke_width_mm: float = 0.11
    preview_height_px: int = 700
    preview_line_width_px: int = 2

    algorithm_name: str = "contraespacios_svg_v3_landscape"


DEFAULT_CONFIG = DrawingConfig()
