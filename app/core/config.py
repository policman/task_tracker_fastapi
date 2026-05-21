from pydantic import BaseModel
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000

class ApiPrefix(BaseModel):
    prefix: str = "/api/v1"

class MinioSettings(BaseModel):
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = False
    bucket_reports: str = "reports"
    bucket_imports: str = "imports"
    bucket_exports: str = "exports"

class CelerySettings(BaseModel):
    broker_url: str
    result_backend: str

class Settings(BaseSettings):
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False

    @property
    def database_url(self) -> str:
        url = MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
        return str(url)

    @property
    def minio(self) -> MinioSettings:
        return MinioSettings(
            endpoint=self.MINIO_ENDPOINT,
            access_key=self.MINIO_ACCESS_KEY,
            secret_key=self.MINIO_SECRET_KEY,
            secure=self.MINIO_SECURE,
        )

    @property
    def celery(self) -> CelerySettings:
        return CelerySettings(
            broker_url=self.CELERY_BROKER_URL,
            result_backend=self.CELERY_RESULT_BACKEND,
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()