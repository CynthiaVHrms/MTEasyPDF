# Integración de autenticación entre Herramientas Conexión y MIA

## Contexto

Herramientas Conexión funciona como punto central de acceso para distintas herramientas internas como SARI, CATIH, NOC, MIA y posiblemente EVA.

MIA vive en otra VM y no maneja usuarios propios ni persiste información de autenticación en base de datos. Su función es únicamente operar como una utilidad para creación de memorias técnicas.

La idea es reutilizar la autenticación existente de Herramientas Conexión mediante JWT.

---

## Flujo propuesto

1. El usuario inicia sesión normalmente en Herramientas Conexión.
2. El usuario selecciona MIA.
3. El backend de Herramientas Conexión valida que el usuario tenga una sesión válida.
4. Herramientas Conexión genera un JWT firmado.
5. El navegador es redirigido hacia MIA incluyendo el JWT en la URL.
6. MIA recibe el JWT.
7. MIA valida:
   - Firma del token.
   - Algoritmo esperado.
   - `issuer`.
   - `audience`.
   - Fecha de inicio (`nbf`), si aplica.
   - Fecha de expiración (`exp`).
8. Si el JWT es válido, MIA permite el acceso.
9. Para no mantener el token visible en la URL, MIA puede guardar el JWT en una cookie `HttpOnly` y redirigir al usuario a una URL limpia.
10. Los endpoints protegidos de MIA reutilizan una única función o middleware para validar el JWT recibido mediante cookie.

---

## Responsabilidades

### Herramientas Conexión

Se encarga de:

- Autenticar al usuario.
- Validar permisos de acceso hacia MIA.
- Generar el JWT.
- Firmar el JWT con el secreto acordado.
- Agregar los datos necesarios del usuario al payload.
- Redirigir al navegador hacia MIA.

Ejemplo:

```text
https://mia.../auth?token=JWT
```

Herramientas Conexión no necesita realizar llamadas adicionales al backend de MIA para autenticar al usuario.

### MIA

Se encarga de:

- Recibir el JWT.
- Validar su firma.
- Validar sus claims.
- Determinar si el token es válido.
- Permitir o rechazar el acceso.
- Mantener temporalmente la autenticación mediante cookie si se requiere navegación entre distintas rutas.

MIA no necesita:

- Crear una tabla de sesiones.
- Guardar JWT en base de datos.
- Consultar la base de datos de Herramientas Conexión.
- Replicar usuarios.
- Mantener sesiones sincronizadas con otras aplicaciones.

---

## Endpoint de entrada en MIA

MIA tendrá un endpoint propio dedicado a recibir el JWT.

Ejemplo:

```text
GET /auth?token=<JWT>
```

El endpoint:

1. Lee el token.
2. Lo valida.
3. Si es correcto, guarda el JWT en una cookie `HttpOnly`.
4. Redirige a la interfaz de MIA.

Flujo:

```text
Herramientas Conexión
        |
        | JWT
        v
GET /auth?token=...
        |
        | validar
        v
Cookie HttpOnly
        |
        v
Redirect /mia
```

---

## Validación del JWT

Ambos sistemas deben compartir el secreto utilizado con HS256.

Ejemplo conceptual:

```python
payload = jwt.decode(
    token,
    JWT_SECRET,
    algorithms=["HS256"],
    issuer="suricato",
    audience="mia",
)
```

La validación debe centralizarse en una función o middleware reutilizable.

```text
validate_token(token)
    |
    +-- firma válida
    +-- algoritmo HS256
    +-- iss válido
    +-- aud válido
    +-- nbf válido
    +-- exp vigente
```

---

## Claims importantes

### `iss` — Issuer

Indica quién generó el token.

```json
{
  "iss": "suricato"
}
```

MIA debe aceptar únicamente tokens emitidos por el sistema esperado.

### `aud` — Audience

Indica para qué sistema fue emitido el token.

Idealmente MIA debería recibir:

```json
{
  "aud": "mia"
}
```

Esto evita que un JWT generado para otra aplicación sea utilizado accidentalmente en MIA.

### `sub` — Subject

Identificador principal del usuario.

Puede utilizarse el UUID/public ID del usuario.

```json
{
  "sub": "29A9FC24-2332-44E0-84B8-795BE1EC91B0"
}
```

### `exp` — Expiration Time

Define cuándo deja de ser válido el JWT.

Es importante que los tokens de redirección tengan una duración limitada.

Recomendación:

```text
5 - 15 minutos
```

El JWT de prueba revisado no incluía `exp`, por lo que antes de pasar a un entorno productivo debe agregarse.

### `nbf` — Not Before

Indica desde qué momento puede comenzar a utilizarse el token.

### `jti` — JWT ID

Identificador único del token.

No es obligatorio para este flujo, pero puede utilizarse si posteriormente se requiere implementar revocación de tokens.

---

## Payload base

Como base, el payload puede mantener la estructura actual:

```json
{
  "idUsuario": "UUID",
  "username": "usuario",
  "company": "HEMAC",
  "iat": 0,
  "nbf": 0,
  "exp": 0,
  "aud": "mia",
  "iss": "suricato",
  "sub": "UUID",
  "jti": "UUID-TOKEN"
}
```

Los nombres y tipos deben quedar acordados entre ambos sistemas para evitar diferencias durante la validación.

---

## Persistencia

MIA no necesita persistencia en base de datos para este esquema.

El propio JWT contiene la información requerida para validar:

- Quién lo emitió.
- Para qué aplicación fue emitido.
- Qué usuario representa.
- Cuándo fue generado.
- Cuándo expira.
- Que el contenido no haya sido modificado.

La firma con el secreto compartido permite verificar su autenticidad.

---

## Cookie en MIA

Después de validar el JWT recibido por URL, es recomendable sacarlo de la URL.

MIA puede guardar temporalmente el token:

```text
mia_auth=<JWT>
```

Con propiedades:

```text
HttpOnly
Secure
SameSite=Lax
```

Después:

```text
/auth?token=JWT
      |
      v
validación
      |
      v
Set-Cookie
      |
      v
302 /mia
```

Así la URL final queda limpia:

```text
https://mia.../mia
```

---

## Acceso directo sin autenticación

Si alguien intenta entrar directamente a MIA sin un JWT/cookie válido:

```text
MIA
 |
 +-- token válido -> continuar
 |
 +-- sin token / token inválido
         |
         v
  Herramientas Conexión
```

De esta manera Herramientas Conexión sigue siendo el punto central de autenticación.

---

## EVA

El mismo patrón puede reutilizarse posteriormente para EVA:

```text
Herramientas Conexión
        |
        +---- JWT aud=mia ----> MIA
        |
        +---- JWT aud=eva ----> EVA
```

La lógica general sería la misma y cada aplicación únicamente valida tokens destinados específicamente para ella.

---

## Puntos pendientes por acordar

- `JWT_SECRET` definitivo.
- Duración del token (`exp`).
- Valor definitivo de `iss`.
- `aud` específico para MIA.
- Payload definitivo.
- URL de entrada de MIA.
- URL de Herramientas Conexión para regresar en caso de autenticación inválida.
- Definir si EVA utilizará exactamente el mismo esquema.

---

## Seguridad

El secreto utilizado durante las pruebas debe considerarse exclusivamente de prueba.

Antes de producción:

- Generar un secreto nuevo y aleatorio.
- Utilizar al menos 32 bytes de entropía para HS256.
- Guardarlo únicamente como variable de entorno.
- No subirlo al repositorio.
- Mantener el mismo secreto únicamente en los servicios que realmente deban firmar o validar estos JWT.

---

## Resumen

```text
LOGIN CENTRAL
Herramientas Conexión
       |
       | genera JWT
       |
       v
redirect hacia MIA
       |
       v
MIA /auth
       |
       | verifica JWT
       |
       v
cookie HttpOnly
       |
       v
MIA
```

No se requiere base de datos adicional ni sincronización de sesiones entre VMs.

Herramientas Conexión mantiene la responsabilidad de autenticación y permisos.

MIA únicamente confía en JWT válidos firmados por Herramientas Conexión.
