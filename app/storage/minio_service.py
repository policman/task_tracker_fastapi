from datetime import timedelta
from minio import Minio
from app.core.config import settings

class MinIOService:
    def __init__(self):
        # Подключаемся к серверу MinIO
        self.client = Minio(
            endpoint=settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.secure
        )

    def init_buckets(self):
        """Проверяет и создает нужные бакеты при старте приложения"""
        buckets = [settings.minio.bucket_reports, settings.minio.bucket_imports]
        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                print(f"Создан бакет: {bucket}")

    def upload_file(
            self,
            bucket: str,
            object_name: str,
            file_path: str,
            content_type: str = "application/octet-stream"
    ) -> str:
        """
        Загружает файл и возвращает временную ссылку на скачивание.
        """
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type
        )
        return self.get_presigned_url(bucket, object_name)

    def get_presigned_url(
            self,
            bucket: str,
            object_name: str,
            expires_days: int = 7
    ) -> str:
        """Генерирует временную ссылку (живет по умолчанию 7 дней)"""
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days)
        )

# Экземпляр сервиса (Синглтон), который мы будем импортировать в роутеры
storage_service = MinIOService()