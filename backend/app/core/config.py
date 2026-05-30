from pathlib import Path

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    app_name: str = "Control de Consumo de Servicios"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
