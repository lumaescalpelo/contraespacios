import json
import math
import re
from datetime import datetime
from pathlib import Path


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value, default=None):
    try:
        if value is None:
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def normalize(value, low, high):
    value = safe_float(value, low)
    if high == low:
        return 0.0
    return clamp((value - low) / (high - low), 0.0, 1.0)


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path = Path(path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def natural_sort_key(path_or_text):
    text = str(path_or_text)
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


def is_probably_jpeg(path, min_size=2048):
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size < min_size:
            return False
        with path.open("rb") as f:
            sig = f.read(3)
        return sig == b"\xff\xd8\xff"
    except Exception:
        return False
