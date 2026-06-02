import os
from datetime import UTC, datetime, timedelta
from typing import BinaryIO

from minio import Minio

from app.core.config import settings


class MinIOService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.secure,
        )

    def list_objects(self, bucket: str, prefix: str = "", recursive: bool = True):
        return self.client.list_objects(bucket_name=bucket, prefix=prefix, recursive=recursive)

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: str,
    ) -> str:
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=self._get_content_type(file_path),
        )
        return self.get_presigned_url(bucket, object_name)

    def upload_stream(
        self,
        bucket: str,
        object_name: str,
        file_data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ):
        self.client.put_object(
            bucket,
            object_name,
            file_data,
            length,
            content_type=content_type,
        )
        return object_name

    def get_presigned_url(self, bucket: str, object_name: str, expires_days: int = 7) -> str:
        return self.client.presigned_get_object(
            bucket_name=bucket, object_name=object_name, expires=timedelta(days=expires_days)
        )

    def download_file(self, bucket: str, object_name: str, file_path: str):
        self.client.fget_object(bucket_name=bucket, object_name=object_name, file_path=file_path)

    def delete_object(self, bucket: str, object_name: str):
        self.client.remove_object(bucket_name=bucket, object_name=object_name)

    def cleanup_old_files(self, bucket: str, days_old: int = 30) -> int:
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
        deleted_count = 0

        objects = self.list_objects(bucket, recursive=True)

        for obj in objects:
            if obj.last_modified < cutoff_date:
                self.delete_object(bucket, obj.object_name)
                deleted_count += 1

        return deleted_count

    def _get_content_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()

        content_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".json": "application/json",
        }

        return content_types.get(ext, "application/octet-stream")


storage_service = MinIOService()
