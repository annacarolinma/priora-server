import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.database.neo4j import verify_connection, ensure_constraints, driver

app = FastAPI(title="Priora API")

# Origem do aplicativo desktop (Electron empacotado): esquema interno que páginas
# da web não conseguem usar, então é seguro liberá-lo sempre.
DESKTOP_APP_ORIGIN = "app://priora"

allowed_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
if DESKTOP_APP_ORIGIN not in allowed_origins:
    allowed_origins.append(DESKTOP_APP_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Imagens do quadro quando o Supabase não está configurado (modo local/Docker)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
async def startup():
    verify_connection()
    ensure_constraints()

@app.get("/")
def read_root():
    return {"message": "Priora backend is running 🚀"}

@app.on_event("shutdown")
async def shutdown():
    driver.close()
