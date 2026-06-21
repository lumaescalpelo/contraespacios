import statistics

from utils import clamp, normalize, safe_float


def _values(records, key):
    vals = []
    for r in records:
        v = safe_float(r["data"].get(key), None)
        if v is not None:
            vals.append(v)
    return vals


def _mean(values):
    return float(statistics.mean(values)) if values else 0.0


def _std(values):
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def analyze_environment(records):
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
        "temperature_std": _std(temp),
        "humidity_std": _std(hum),
        "aqi_std": _std(aqi),
        "tvoc_std": _std(tvoc),
        "eco2_std": _std(eco2),
    }

    # Influencia sutil.
    hum_n = normalize(stats["humidity_mean"], 20, 90)
    aqi_n = normalize(stats["aqi_mean"], 1, 5)
    tvoc_n = normalize(stats["tvoc_mean"], 0, 600)
    eco2_n = normalize(stats["eco2_mean"], 400, 2000)
    variability = clamp(
        0.3 * normalize(stats["humidity_std"], 0, 15) +
        0.3 * normalize(stats["tvoc_std"], 0, 200) +
        0.4 * normalize(stats["eco2_std"], 0, 400),
        0.0, 1.0,
    )

    visual = {
        "contour_weight": clamp(0.70 + eco2_n * 0.15, 0.68, 0.95),
        "band_density": clamp(0.85 + hum_n * 0.12 - variability * 0.08, 0.72, 1.0),
        "band_amplitude_factor": clamp(0.85 + tvoc_n * 0.25 + aqi_n * 0.08, 0.80, 1.20),
        "internal_weight": clamp(0.75 + variability * 0.15, 0.70, 1.0),
        "stroke_width_mm": clamp(0.10 + aqi_n * 0.025 + tvoc_n * 0.02, 0.10, 0.15),
    }
    return stats, visual
