from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from app.core.config import settings

class MinIOService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.secure
        )

    def upload_file(
            self,
            bucket: str,
            object_name: str,
            file_path: str,
            content_type: str = "application/octet-stream"
    ) -> str:
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type
        )
        return self.get_presigned_url(bucket, object_name)

    def upload_stream(
        self,
        bucket: str,
        object_name: str,
        file_data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream"
    ):
        self.client.put_object(
            bucket,
            object_name,
            file_data,
            length,
            content_type=content_type,
        )
        return object_name

    def get_presigned_url(
            self,
            bucket: str,
            object_name: str,
            expires_days: int = 7
    ) -> str:
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days)
        )

    def download_file(self, bucket: str, object_name: str, file_path: str):
        self.client.fget_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path
        )


storage_service = MinIOService()