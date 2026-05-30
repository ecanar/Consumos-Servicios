from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import dashboard, facturas, lecturas
from app.core.config import settings
from app.db.session import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/fotos", StaticFiles(directory="data/fotos_medidores"), name="fotos")

app.include_router(facturas.router, prefix="/api/facturas", tags=["Facturas"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(lecturas.router, prefix="/api/lecturas-semanales", tags=["Lecturas Semanales"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
