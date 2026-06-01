from app.core.config import settings


def allowed_extensions() -> set[str]:
    return {
        ext.strip().lower().lstrip(".")
        for ext in settings.UPLOAD_ALLOWED_EXTENSIONS.split(",")
        if ext.strip()
    }


def allowed_extensions_display() -> list[str]:
    return sorted(allowed_extensions())


def accept_header_value() -> str:
    return ",".join(f".{ext}" for ext in allowed_extensions_display())


def get_file_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def upload_limits_payload() -> dict:
    exts = allowed_extensions_display()
    return {
        "max_size_mb": settings.UPLOAD_MAX_SIZE_MB,
        "max_size_bytes": settings.UPLOAD_MAX_SIZE_BYTES,
        "allowed_extensions": exts,
        "accept": accept_header_value(),
        "hint": f"支持 {', '.join(exts)}，单文件不超过 {settings.UPLOAD_MAX_SIZE_MB}MB",
    }
