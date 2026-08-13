"""
auth.py — Validación centralizada de JWT para MIA.

MIA no maneja usuarios propios ni sesiones en base de datos.
Toda la autenticación se delega a Herramientas Conexión, que genera
un JWT firmado con un secreto compartido (HS256) y lo entrega a MIA
mediante una redirección en el navegador.

Este módulo es la única pieza del backend que entiende de JWT.
Cualquier otro componente que necesite proteger un endpoint debe
usar la dependencia `require_auth` de dependencies.py, no llamar
a este módulo directamente.
"""

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


class TokenValidationError(Exception):
    """
    Error de validación de JWT.

    Se lanza con un mensaje descriptivo cuando el token no supera
    alguna de las verificaciones (firma, claims, expiración, etc.).
    El mensaje se expone directamente al cliente en el HTTP 401.
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def validate_token(token: str) -> dict:
    """
    Valida un JWT emitido por Herramientas Conexión.

    Verificaciones aplicadas (en orden):
    1. JWT_SECRET configurado en el servidor.
    2. Firma HMAC-SHA256 con el secreto compartido.
    3. Algoritmo: únicamente HS256 está permitido.
       (Fijar la lista de algoritmos protege contra el ataque
        "algorithm confusion" donde un atacante cambia alg a "none".)
    4. iss  — debe coincidir con JWT_ISSUER (.env).
    5. aud  — debe coincidir con JWT_AUDIENCE (.env).
    6. nbf  — el token no puede usarse antes de esta fecha.
    7. exp  — el token no puede usarse después de esta fecha.
    8. Claims requeridos: iss, aud, sub deben estar presentes.

    Parámetros:
        token: JWT en formato compacto (header.payload.signature).

    Retorna:
        dict con el payload decodificado si el token es válido.

    Lanza:
        TokenValidationError con un mensaje descriptivo si falla
        cualquiera de las verificaciones anteriores.
    """
    if not settings.jwt_secret:
        raise TokenValidationError("JWT_SECRET no configurado en el servidor.")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            # Fijar explícitamente el algoritmo — nunca aceptar "none" ni RS256
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
                # iss, aud y sub son obligatorios en todos los tokens de HC
                "require": ["iss", "aud", "sub"],
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenValidationError("El token ha expirado.")
    except jwt.ImmatureSignatureError:
        raise TokenValidationError("El token aún no es válido (nbf).")
    except jwt.InvalidIssuerError:
        raise TokenValidationError("Emisor del token inválido.")
    except jwt.InvalidAudienceError:
        raise TokenValidationError("Audiencia del token inválida.")
    except jwt.MissingRequiredClaimError as e:
        raise TokenValidationError(f"Claim requerido ausente: {e}.")
    except InvalidTokenError as e:
        # Cubre firma incorrecta, formato malformado, algoritmo no permitido, etc.
        raise TokenValidationError(f"Token inválido: {e}.")
