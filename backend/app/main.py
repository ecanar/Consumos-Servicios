import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import dashboard, facturas, lecturas
from app.core.config import settings
from app.db.session import Base, engine


# Generar google_key.json en caliente si existe la variable de entorno en Railway
google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_creds_json:
    try:
        with open("google_key.json", "w") as f:
            f.write(google_creds_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("google_key.json")
        print("[OCR] Google Cloud Vision inicializado exitosamente desde variables de entorno.")
    except Exception as e:
        print(f"[OCR] Error al reconstruir llave de Google: {e}")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data/fotos_medidores", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="data/fotos_medidores"), name="fotos")

app.include_router(facturas.router, prefix="/api/facturas", tags=["Facturas"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(lecturas.router, prefix="/api/lecturas-semanales", tags=["Lecturas Semanales"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
