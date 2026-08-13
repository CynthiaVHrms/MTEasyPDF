# Autenticación JWT en MIA

## Contexto

MIA vive en una VM separada y no maneja usuarios propios ni base de datos de sesiones. La autenticación se delega completamente a **Herramientas Conexión**, que actúa como punto central de acceso para todas las herramientas internas (SARI, CATIH, NOC, MIA).

El esquema utiliza **JWT firmados con HS256** y un secreto compartido. MIA únicamente verifica tokens, nunca los emite.

---

## Flujo completo

```
Usuario inicia sesión en Herramientas Conexión
                │
                │  1. HC valida sesión del usuario
                │  2. HC genera JWT firmado con HS256
                │  3. HC redirige al navegador
                ▼
http://<host>/mia/auth?token=<JWT>
                │
                │  Next.js — Route Handler /mia/auth
                │
                ├── token ausente o inválido ──► redirect REDIRECT_ON_FAILURE
                │
                └── token válido
                        │
                        │  Set-Cookie: mia_auth=<JWT>  (HttpOnly)
                        ▼
                redirect /mia  (URL limpia, sin token visible)
                        │
                        │  Next.js Middleware (cada request)
                        │
                        ├── sin cookie / cookie inválida ──► redirect REDIRECT_ON_FAILURE
                        │
                        └── cookie válida ──► continuar normalmente
                                │
                                ▼
                          Aplicación MIA
```

---

## Arquitectura: ¿por qué auth en el frontend?

El frontend (Next.js, puerto 3001/3004) y el backend (FastAPI) corren en puertos distintos. Las cookies del navegador están ligadas a un dominio + puerto, lo que significa que una cookie seteada por el backend en su puerto **no se comparte automáticamente** con el frontend.

Por esta razón, la validación inicial del JWT y el seteo de la cookie se hacen en Next.js, que corre completamente en el servidor (el secreto nunca llega al navegador). El backend mantiene su propia validación de JWT desactivable por variable de entorno.

---

## Archivos involucrados

### Backend (FastAPI)

| Archivo | Responsabilidad |
|---|---|
| `app/core/config.py` | Variables de entorno JWT (`AUTH_ENABLED`, `JWT_SECRET`, etc.) |
| `app/core/auth.py` | Función `validate_token()` — toda la lógica de verificación JWT |
| `app/core/dependencies.py` | Dependencia `require_auth` — inyectable en cualquier endpoint |
| `app/main.py` | `/health` pública; todos los demás routers usan `require_auth` |
| `.env` | Variables de entorno locales (no subir al repositorio) |

### Frontend (Next.js)

| Archivo | Responsabilidad |
|---|---|
| `app/auth/route.ts` | Route Handler — recibe el JWT, lo valida, setea cookie, redirige |
| `middleware.ts` | Protege todas las rutas; verifica la cookie en cada request |
| `.env.local` | Variables de entorno locales (no subir al repositorio) |

---

## Variables de entorno

### Backend — `backend/.env`

```env
# false = modo debug (sin validación JWT)
# true  = producción (cookie mia_auth obligatoria)
AUTH_ENABLED=false

# Secreto compartido con Herramientas Conexión
JWT_SECRET=<secreto>

JWT_ISSUER=suricato
JWT_AUDIENCE=mia

# URL de Herramientas Conexión para redirigir en caso de auth inválida
REDIRECT_ON_FAILURE=http://<url-herramientas-conexion>
```

### Frontend — `frontend/.env.local`

```env
# false = modo debug (sin validación JWT)
# true  = producción (JWT obligatorio)
AUTH_ENABLED=true

# Mismo secreto que el backend
JWT_SECRET=<secreto>

JWT_ISSUER=suricato
JWT_AUDIENCE=mia

REDIRECT_ON_FAILURE=http://<url-herramientas-conexion>

# false en HTTP, true cuando haya HTTPS disponible
COOKIE_SECURE=false

# URL base del backend FastAPI
NEXT_PUBLIC_API_URL=http://<ip>:<puerto-backend>
```

---

## Modo debug (desarrollo)

Con `AUTH_ENABLED=false`:

- **Frontend:** El middleware deja pasar todos los requests sin verificar cookie. El endpoint `/mia/auth` redirige directamente a `/mia` sin validar el token.
- **Backend:** La dependencia `require_auth` retorna `None` sin leer ninguna cookie. Todos los endpoints responden normalmente.

Esto permite desarrollar sin necesidad de pasar por el flujo de Herramientas Conexión.

> **Nunca desplegar a producción con `AUTH_ENABLED=false`.**

---

## Cookie `mia_auth`

| Propiedad | Valor | Razón |
|---|---|---|
| `HttpOnly` | `true` | JavaScript del cliente no puede leerla (previene XSS) |
| `SameSite` | `Lax` | Protección básica CSRF; permite redirecciones cross-site |
| `Secure` | `false` en dev / `true` en prod | Requiere HTTPS — activar cuando haya dominio |
| `Path` | `/` | Disponible en todas las rutas |

---

## Claims del JWT esperados

| Claim | Descripción | Valor esperado |
|---|---|---|
| `iss` | Emisor | `suricato` |
| `aud` | Audiencia | `mia` |
| `sub` | Identificador del usuario (UUID) | UUID del usuario |
| `exp` | Expiración | Fecha Unix — **obligatorio en producción** |
| `nbf` | No válido antes de | Fecha Unix |
| `iat` | Emitido en | Fecha Unix |
| `idUsuario` | UUID del usuario en HC | UUID |
| `username` | Nombre de usuario | `luis.morales` |
| `company` | Empresa | `HEMAC` |
| `jti` | ID único del token | UUID del token |

### Payload de ejemplo

```json
{
  "idUsuario": "29A9FC24-2332-44E0-84B8-795BE1EC91B0",
  "username": "luis.morales",
  "company": "HEMAC",
  "iat": 1786380415,
  "nbf": 1786380415,
  "exp": 1786381315,
  "aud": "mia",
  "iss": "suricato",
  "sub": "29A9FC24-2332-44E0-84B8-795BE1EC91B0",
  "jti": "82fa2a3f-e2bf-47d6-9756-cda9bd7d0d26"
}
```

---

## Validaciones aplicadas al JWT

El siguiente checklist se aplica en ambos lados (frontend y backend):

- [x] Firma HMAC-SHA256 con el secreto compartido
- [x] Algoritmo fijado a `HS256` — protege contra el ataque *algorithm confusion* (`alg: none`)
- [x] `iss` debe coincidir con `JWT_ISSUER`
- [x] `aud` debe coincidir con `JWT_AUDIENCE`
- [x] `nbf` — el token no se puede usar antes de esta fecha
- [x] `exp` — el token no se puede usar después de esta fecha *(requiere que HC incluya este claim)*
- [x] Claims requeridos: `iss`, `aud`, `sub` deben estar presentes

---

## Paso a producción

Lista de cambios antes de salir a producción:

- [ ] Confirmar con Herramientas Conexión que el token incluye `exp` (5-15 minutos recomendados)
- [ ] Confirmar que el `aud` del token sea `"mia"` y actualizar `JWT_AUDIENCE=mia` en ambos `.env`
- [ ] Generar un nuevo `JWT_SECRET` de al menos 32 bytes de entropía
- [ ] Guardar el secreto únicamente como variable de entorno (nunca en el código)
- [ ] Activar `AUTH_ENABLED=true` en ambos servicios
- [ ] Activar `COOKIE_SECURE=true` cuando haya HTTPS disponible
- [ ] Configurar `REDIRECT_ON_FAILURE` con la URL real de Herramientas Conexión
- [ ] Verificar que `.env` y `.env.local` estén en `.gitignore`

---

## Extensión a otras herramientas (EVA, etc.)

El mismo patrón puede replicarse para otras herramientas internas. Herramientas Conexión emite tokens con `aud` diferente para cada destino:

```
Herramientas Conexión
        │
        ├── JWT aud=mia ──► MIA
        │
        └── JWT aud=eva ──► EVA
```

Cada herramienta valida únicamente tokens destinados específicamente para ella, evitando que un token de una herramienta sea reutilizado en otra.
