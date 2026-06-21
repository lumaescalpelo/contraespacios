"""
Carga de sesiones desde ~/data/sessions/Sxx.
"""

from pathlib import Path

from utils import ensure_dir, is_probably_jpeg, load_json, natural_sort_key, safe_float


REQUIRED_ENV_KEYS = ("temperature", "humidity", "aqi", "tvoc", "eco2")


def validate_environment_data(data):
    if not isinstance(data, dict):
        return False

    if data.get("ok") is not True:
        return False

    if data.get("aht_ok") is not True:
        return False

    if data.get("ens_ok") is not True:
        return False

    for key in REQUIRED_ENV_KEYS:
        if safe_float(data.get(key), None) is None:
            return False

    return True


def list_valid_photos(photos_dir, max_photos=None):
    photos_dir = Path(photos_dir)
    if not photos_dir.exists():
        return []

    files = sorted(
        list(photos_dir.glob("*.jpg")) + list(photos_dir.glob("*.jpeg")),
        key=natural_sort_key
    )

    valid = [p for p in files if is_probably_jpeg(p)]

    if max_photos is not None:
        valid = valid[-int(max_photos):]

    return valid


def list_valid_environment(environment_dir):
    environment_dir = Path(environment_dir)
    if not environment_dir.exists():
        return []

    records = []

    for path in sorted(environment_dir.glob("*.json"), key=natural_sort_key):
        try:
            data = load_json(path)
        except Exception:
            continue

        if validate_environment_data(data):
            records.append({
                "path": path,
                "data": data
            })

    return records


def get_session_paths(data_root, session_id):
    data_root = Path(data_root).expanduser()
    session_dir = data_root / "sessions" / session_id

    return {
        "data_root": data_root,
        "session": session_dir,
        "session_json": session_dir / "session.json",
        "photos": session_dir / "photos",
        "environment": session_dir / "environment",
        "output": session_dir / "output",
    }


def load_session(data_root, session_id, max_photos=None):
    paths = get_session_paths(data_root, session_id)

    if not paths["session"].exists():
        raise FileNotFoundError(f"No existe la sesión: {paths['session']}")

    ensure_dir(paths["output"])

    photos = list_valid_photos(paths["photos"], max_photos=max_photos)
    environment = list_valid_environment(paths["environment"])

    if len(photos) == 0:
        raise ValueError(f"La sesión {session_id} no tiene fotos válidas.")

    if len(environment) == 0:
        raise ValueError(f"La sesión {session_id} no tiene lecturas ambientales válidas.")

    return {
        "session_id": session_id,
        "paths": paths,
        "photos": photos,
        "environment": environment,
    }
