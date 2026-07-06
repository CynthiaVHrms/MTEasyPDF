from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router
from app.api.routes.protocols import router as protocols_router

app = FastAPI(
    title="MTEasyPDF Web API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3000",
        "http://10.241.1.8:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Job-Id",
        "X-Total-Enlaces",
        "X-Total-Sitios",
        "X-Total-Clasificaciones",
        "X-Total-Documentos-Generados",
    ],
)

app.include_router(health_router)
app.include_router(reports_router)
app.include_router(protocols_router)


# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from app.api.routes.health import router as health_router
# from app.api.routes.reports import router as reports_router

# app = FastAPI(
#     title="MTEasyPDF Web API",
#     version="0.1.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",
#         "http://127.0.0.1:3000",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(health_router)
# app.include_router(reports_router)




