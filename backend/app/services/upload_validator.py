from fastapi import UploadFile

from app.core.config import settings
from app.core.upload import allowed_extensions_display, get_file_extension


def validate_upload_file(file: UploadFile, size: int) -> str:
    filename = file.filename or ""
    ext = get_file_extension(filename)

    if not ext:
        allowed = ", ".join(allowed_extensions_display())
        raise ValueError(f"无法识别文件类型，仅允许: {allowed}")

    allowed = settings.allowed_upload_extensions
    if ext not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"不支持的文件类型 [{ext}]，仅允许: {allowed_str}")

    if size <= 0:
        raise ValueError("文件不能为空")

    if size > settings.UPLOAD_MAX_SIZE_BYTES:
        size_mb = size / (1024 * 1024)
        raise ValueError(
            f"文件大小 {size_mb:.1f}MB 超过上限 "
            f"{settings.UPLOAD_MAX_SIZE_MB}MB"
        )

    return ext
