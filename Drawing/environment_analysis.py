"""Análisis ambiental con influencia moderada, no dominante."""

import statistics

from utils import clamp, normalize, safe_float


def _values(records, key):
    values = []
    for record in records:
        value = safe_float(record["data"].get(key), None)
        if value is not None:
            values.append(value)
    return values


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
    }

    temp_n = normalize(stats["temperature_mean"], 10, 38)
    hum_n = normalize(stats["humidity_mean"], 20, 90)
    aqi_n = normalize(stats["aqi_mean"], 1, 5)
    tvoc_n = normalize(stats["tvoc_mean"], 0, 600)
    eco2_n = normalize(stats["eco2_mean"], 400, 2000)

    variability = clamp(
        0.30 * normalize(stats["temperature_std"], 0, 4) +
        0.25 * normalize(stats["humidity_std"], 0, 15) +
        0.25 * normalize(stats["tvoc_std"], 0, 200) +
        0.20 * normalize(stats["eco2_std"], 0, 400),
        0.0, 1.0
    )

    # En v2 la foto manda y el ambiente sólo matiza.
    visual = {
        "density": clamp(0.75 + variability * 0.20 + hum_n * 0.05, 0.72, 1.0),
        "scanline_factor": clamp(0.85 + hum_n * 0.15 + variability * 0.15, 0.80, 1.15),
        "scan_amplitude_factor": clamp(0.95 + tvoc_n * 0.20 + aqi_n * 0.10, 0.90, 1.25),
        "edge_weight": clamp(0.80 + aqi_n * 0.20 + variability * 0.10, 0.75, 1.15),
        "contour_weight": clamp(0.65 + eco2_n * 0.20 + variability * 0.10, 0.60, 1.0),
        "tone_gamma": clamp(0.90 + temp_n * 0.10 - hum_n * 0.05, 0.82, 1.05),
        "stroke_width_mm": clamp(0.08 + aqi_n * 0.05 + tvoc_n * 0.03, 0.08, 0.16),
    }

    return stats, visual
