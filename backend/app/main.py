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
from fastapi.responses import FileResponse
from app.core.config import PROJECT_ROOT

# Montar los assets estáticos compilados del Frontend si existen
assets_dir = PROJECT_ROOT / "frontend" / "dist" / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

app.mount("/fotos", StaticFiles(directory="data/fotos_medidores"), name="fotos")

app.include_router(facturas.router, prefix="/api/facturas", tags=["Facturas"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(lecturas.router, prefix="/api/lecturas-semanales", tags=["Lecturas Semanales"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# Ruta comodín (catch-all) para redirigir rutas de React al index.html en producción
@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    # Si la ruta empieza con 'api' o 'fotos', pero no se resolvió arriba, devolvemos un 404 real
    if catchall.startswith("api") or catchall.startswith("fotos"):
        return {"detail": "Ruta de API no encontrada"}
        
    index_path = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"detail": "El Frontend aún no ha sido compilado. Ejecuta 'npm run build' en la carpeta frontend."}
