from pydantic import BaseModel
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class ApiPrefix(BaseModel):
    prefix: str = "/api/v1"


class MinioSettings(BaseSettings):
    endpoint: str = "localhost:9000"
    access_key: str = "admin"
    secret_key: str = "admin123"
    secure: bool = False

    bucket_reports: str = "reports"
    bucket_imports: str = "imports"

class CelerySettings(BaseSettings):
    broker_url: str = "amqp://guest:guest@127.0.0.1:5672//"
    result_backend: str = "redis://127.0.0.1:6379/0"


class Settings(BaseSettings):
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()
    minio: MinioSettings = MinioSettings()
    celery: CelerySettings = CelerySettings()

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()