import uuid

from app.core.config import settings
from app.core.minio_client import client

ALLOWED_TYPES = ["pdf", "txt", "md"]


def save_file(file, user_id: int, knowledge_base_id: int):
    ext = file.filename.split(".")[-1].lower()

    if ext not in ALLOWED_TYPES:
        raise ValueError("Unsupported file type")

    file_id = str(uuid.uuid4())
    object_name = f"users/{user_id}/kbs/{knowledge_base_id}/{file_id}.{ext}"

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=file.file,
        length=size,
        content_type=file.content_type,
    )

    return object_name, size
