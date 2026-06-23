from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router

app = FastAPI(
    title="MTEasyPDF Web API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(reports_router)




