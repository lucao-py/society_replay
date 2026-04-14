import json
import threading
from pathlib import Path
from typing import Any

_storage_lock = threading.Lock()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_json_file(path: Path, default: Any) -> None:
    with _storage_lock:
        if not path.exists():
            path.write_text(
                json.dumps(default, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


def read_json(path: Path, default: Any) -> Any:
    with _storage_lock:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default


def write_json(path: Path, data: Any) -> None:
    with _storage_lock:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(path)


def append_json_item(path: Path, item: Any, default: Any = None) -> None:
    if default is None:
        default = []

    with _storage_lock:
        if not path.exists():
            current = default
        else:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = default

        current.append(item)

        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(current, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(path)