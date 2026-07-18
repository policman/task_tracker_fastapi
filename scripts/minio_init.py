from logging import INFO, basicConfig, getLogger

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

basicConfig(level=INFO)
logger = getLogger("init_minio")


def init_buckets():
    logger.info("Initializing Minio and create buckets")

    client = Minio(
        endpoint=settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
    )

    buckets = [
        settings.minio.bucket_imports,
        settings.minio.bucket_exports,
        settings.minio.bucket_reports,
    ]

    try:
        for bucket in buckets:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"Bucket {bucket} created")
            else:
                logger.info(f"Bucket {bucket} already exists")
    except S3Error as e:
        logger.error(f"Error creating Minio: {e}")
    except Exception as e:
        logger.error(f"Unrealized error: {e}")


if __name__ == "__main__":
    init_buckets()
