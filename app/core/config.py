from pydantic import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSGRES_USER: str
    POSGRES_PASSWORD: str
    POSGRES_HOST: str
    POSGRES_PORT: str
    POSGRES_DB: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()