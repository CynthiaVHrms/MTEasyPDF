from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno o .env.

    Variables de entorno relevantes para autenticación:

        AUTH_ENABLED      bool    Activar/desactivar validación JWT.
                                  false = modo debug (sin auth).
                                  true  = producción (JWT obligatorio).
                                  Default: true.

        JWT_SECRET        str     Secreto compartido con Herramientas Conexión
                                  para firmar/verificar tokens HS256.
                                  Nunca subir al repositorio.

        JWT_ALGORITHM     str     Algoritmo de firma. Solo se acepta HS256.
                                  Default: HS256.

        JWT_ISSUER        str     Valor esperado del claim 'iss'.
                                  Debe coincidir con lo que genera HC.
                                  Default: suricato.

        JWT_AUDIENCE      str     Valor esperado del claim 'aud'.
                                  Debe ser 'mia' en producción.
                                  Default: mia.

        REDIRECT_ON_FAILURE str   URL de Herramientas Conexión a la que
                                  redirigir cuando el token es inválido.
                                  Default: http://localhost.
    """

    app_name: str = "MTEasyPDF Web"
    storage_dir: Path = Path("C:/mteasypdf_jobs")
    max_upload_size_mb: int = 3072
    retention_days: int = 7

    # --- Autenticación JWT ---
    # Poner AUTH_ENABLED=false en .env para deshabilitar auth (modo debug/desarrollo)
    auth_enabled: bool = True
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "suricato"
    jwt_audience: str = "mia"
    # URL de Herramientas Conexión a la que redirigir si el token es inválido o inexistente
    redirect_on_failure: str = "http://localhost"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
settings.storage_dir = settings.storage_dir.resolve()
settings.storage_dir.mkdir(parents=True, exist_ok=True)