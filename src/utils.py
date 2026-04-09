import uuid


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


def format_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60

    if hh > 0:
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    return f"{mm:02d}:{ss:02d}"


def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.replace(" ", "_")