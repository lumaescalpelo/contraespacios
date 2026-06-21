"""
Análisis ambiental.

Convierte lecturas físicas en parámetros visuales. La idea es que sesiones con
ambientes similares produzcan transformaciones similares y sesiones distintas
produzcan dibujos distinguibles.
"""

import statistics

from utils import clamp, normalize, safe_float


def _values(records, key):
    result = []
    for record in records:
        value = safe_float(record["data"].get(key), None)
        if value is not None:
            result.append(value)
    return result


def _mean(values):
    return float(statistics.mean(values)) if values else 0.0


def _stdev(values):
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def analyze_environment(records):
    if not records:
        raise ValueError("No hay lecturas ambientales válidas.")

    temp = _values(records, "temperature")
    hum = _values(records, "humidity")
    aqi = _values(records, "aqi")
    tvoc = _values(records, "tvoc")
    eco2 = _values(records, "eco2")

    stats = {
        "readings_used": len(records),

        "temperature_mean": _mean(temp),
        "humidity_mean": _mean(hum),
        "aqi_mean": _mean(aqi),
        "tvoc_mean": _mean(tvoc),
        "eco2_mean": _mean(eco2),

        "temperature_std": _stdev(temp),
        "humidity_std": _stdev(hum),
        "aqi_std": _stdev(aqi),
        "tvoc_std": _stdev(tvoc),
        "eco2_std": _stdev(eco2),

        "temperature_min": min(temp) if temp else None,
        "temperature_max": max(temp) if temp else None,
        "humidity_min": min(hum) if hum else None,
        "humidity_max": max(hum) if hum else None,
        "tvoc_min": min(tvoc) if tvoc else None,
        "tvoc_max": max(tvoc) if tvoc else None,
        "eco2_min": min(eco2) if eco2 else None,
        "eco2_max": max(eco2) if eco2 else None,
    }

    temp_n = normalize(stats["temperature_mean"], 10, 38)
    hum_n = normalize(stats["humidity_mean"], 20, 90)
    aqi_n = normalize(stats["aqi_mean"], 1, 5)
    tvoc_n = normalize(stats["tvoc_mean"], 0, 600)
    eco2_n = normalize(stats["eco2_mean"], 400, 2000)

    temp_var_n = normalize(stats["temperature_std"], 0, 4)
    hum_var_n = normalize(stats["humidity_std"], 0, 15)
    tvoc_var_n = normalize(stats["tvoc_std"], 0, 200)
    eco2_var_n = normalize(stats["eco2_std"], 0, 400)

    variability = clamp(
        0.30 * temp_var_n +
        0.25 * hum_var_n +
        0.25 * tvoc_var_n +
        0.20 * eco2_var_n,
        0.0,
        1.0
    )

    visual = {
        "temperature_norm": temp_n,
        "humidity_norm": hum_n,
        "aqi_norm": aqi_n,
        "tvoc_norm": tvoc_n,
        "eco2_norm": eco2_n,
        "variability_norm": variability,

        "density": clamp(0.30 + tvoc_n * 0.35 + eco2_n * 0.20 + aqi_n * 0.15, 0.25, 1.0),
        "noise_mm": clamp(0.05 + tvoc_n * 0.28 + variability * 0.22, 0.03, 0.55),
        "wave_frequency": clamp(1.0 + hum_n * 3.0 + eco2_n * 2.5, 1.0, 6.5),
        "atmosphere_lines": int(round(6 + hum_n * 6 + eco2_n * 5 + aqi_n * 3)),
        "phase": (stats["temperature_mean"] * 0.31 + stats["humidity_mean"] * 0.17 + stats["tvoc_mean"] * 0.013) % 6.283185,
        "stroke_width_mm": clamp(0.08 + aqi_n * 0.07 + tvoc_n * 0.04, 0.08, 0.20),
    }

    return stats, visual
