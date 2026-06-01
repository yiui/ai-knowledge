import uuid

from fastapi import UploadFile

from app.core.config import settings
from app.core.minio_client import client
from app.services.upload_validator import validate_upload_file


def read_upload_size(file: UploadFile) -> int:
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    return size


def save_file(file: UploadFile, user_id: int, knowledge_base_id: int):
    size = read_upload_size(file)
    ext = validate_upload_file(file, size)

    file_id = str(uuid.uuid4())
    object_name = f"users/{user_id}/kbs/{knowledge_base_id}/{file_id}.{ext}"

    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=file.file,
        length=size,
        content_type=file.content_type,
    )

    return object_name, size
