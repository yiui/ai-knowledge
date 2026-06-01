# app/services/minio_service.py

from minio import Minio
from app.core.config import settings
from io import BytesIO

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)


def download_file(object_name: str) -> str:
    response = client.get_object("documents", object_name)

    data = response.read()

    local_path = f"/tmp/{object_name}"

    with open(local_path, "wb") as f:
        f.write(data)

    return local_path