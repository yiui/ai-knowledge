from minio import Minio
from app.core.config import settings

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)


def ensure_bucket():
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


def download_from_minio(object_name: str) -> str:
    file_path = f"/tmp/{object_name}"

    client.fget_object(
        settings.MINIO_BUCKET,
        object_name,
        file_path
    )

    return file_path