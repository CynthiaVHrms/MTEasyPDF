from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.protocols import router as protocols_router
from app.api.routes.reports import router as reports_router
from app.api.routes.tagged_documents import (
    router as tagged_documents_router,
)


app = FastAPI(
    title="MTEasyPDF Web API",
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://10.241.1.8:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-Id",
        "X-Job-Id",
        "X-Total-Enlaces",
        "X-Total-Sitios",
        "X-Total-Clasificaciones",
        "X-Total-Documentos-Generados",
        "X-Total-Imagenes-Omitidas",
        "X-Total-Etiquetas",
        "X-Total-Evidencias",
        "X-Total-Etiquetas-Reemplazadas",
        "X-Total-Etiquetas-No-Encontradas",
        "X-Total-Imagenes-Insertadas",
        "X-Total-Imagenes-No-Encontradas",
    ],
)


app.include_router(health_router)
app.include_router(reports_router)
app.include_router(protocols_router)
app.include_router(tagged_documents_router)