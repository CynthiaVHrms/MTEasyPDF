"""
dependencies.py — Dependencias reutilizables de FastAPI.

Contiene `require_auth`, la dependencia que se inyecta en los routers
protegidos. Centraliza la lógica de "¿está autenticado este request?"
para que los endpoints no necesiten saber nada de JWT.

Uso en un router:
    @router.get("/endpoint")
    def mi_endpoint(payload: dict | None = Depends(require_auth)):
        ...

O directamente en include_router (aplicado a todos los endpoints del router):
    app.include_router(mi_router, dependencies=[Depends(require_auth)])
"""

from fastapi import Cookie, HTTPException, status

from app.core.auth import TokenValidationError, validate_token
from app.core.config import settings


def require_auth(mia_auth: str | None = Cookie(default=None)) -> dict | None:
    """
    Protege un endpoint verificando la cookie JWT 'mia_auth'.

    Comportamiento según AUTH_ENABLED:

        AUTH_ENABLED=false (modo debug/desarrollo):
            Retorna None sin verificar nada. Todos los endpoints
            responden normalmente. Útil para desarrollo local sin
            necesidad de pasar por el flujo de Herramientas Conexión.

        AUTH_ENABLED=true (producción):
            Lee la cookie 'mia_auth' del request.
            - Sin cookie  → HTTP 401
            - Cookie inválida o expirada → HTTP 401
            - Cookie válida → retorna el payload del JWT

    La cookie 'mia_auth' la setea el frontend (Next.js) en el
    endpoint /mia/auth después de validar el JWT recibido desde
    Herramientas Conexión. El backend la recibe en requests
    que el frontend haga con credenciales (credentials: 'include').

    Retorna:
        dict con el payload del JWT si está autenticado.
        None si AUTH_ENABLED=false.

    Lanza:
        HTTPException 401 si el token está ausente o es inválido.
    """
    if not settings.auth_enabled:
        # Modo debug — auth desactivada por configuración
        return None

    if not mia_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Accede a MIA desde Herramientas Conexión.",
        )

    try:
        payload = validate_token(mia_auth)
        return payload
    except TokenValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
        )
