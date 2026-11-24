from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./agenttrainer.db"
    jwt_secret: str = "local-development-secret-change-me"
    access_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def cors_list(self) -> list[str]: return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
