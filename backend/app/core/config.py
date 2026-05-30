import os
from pathlib import Path

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Railway y Heroku a veces proveen 'postgres://', pero SQLAlchemy requiere 'postgresql://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    return f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"


class Settings(BaseModel):
    app_name: str = "Control de Consumo de Servicios"
    database_url: str = get_database_url()
    cors_origins: list[str] = ["http://localhost:5173", "https://consumo-servicios.netlify.app", "*"]


settings = Settings()
