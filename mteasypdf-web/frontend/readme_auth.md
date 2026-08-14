# README AUTH - MIA Frontend

Este documento describe la implementacion de autenticacion JWT en el frontend de MIA (Next.js 16), incluyendo flujo, rutas, variables, decisiones tecnicas, riesgos y troubleshooting.

## 1. Objetivo

Proteger la aplicacion web bajo /mia para que:

1. Sin sesion valida, el usuario sea enviado a Herramientas Conexion.
2. Con token valido, se cree cookie de sesion y entre a la app.
3. Se soporte integracion legacy donde llega /auth?<JWT> (sin token=).
4. Se eviten redirecciones reescritas por reverse proxy.

## 2. Archivos clave

1. proxy de seguridad global
- proxy.ts

2. endpoint de recepcion de token
- app/auth/route.ts

3. endpoint de salida segura hacia HC
- app/auth/failure/route.ts

4. variables de entorno
- .env.local

## 3. Variables de entorno

Estas variables gobiernan el comportamiento:

1. AUTH_ENABLED
- true: auth activa.
- false: modo debug, no bloquea acceso.

2. JWT_SECRET
- secreto compartido para verificar firma HS256.

3. JWT_ISSUER
- claim iss esperado.

4. JWT_AUDIENCE
- claim aud esperado.

5. REDIRECT_ON_FAILURE
- URL destino cuando falla auth.
- ejemplo actual: https://app.grupohemac.com.mx:3003/select-platform

6. COOKIE_SECURE
- false en HTTP local/proxy no TLS.
- true en HTTPS real.

## 4. Flujo completo de autenticacion

### 4.1 Entrada a la app protegida

1. Usuario entra a /mia (o ruta protegida).
2. proxy.ts intercepta.
3. Si no hay cookie mia_auth, redirige a /mia/auth/failure.
4. app/auth/failure/route.ts responde HTML con redireccion cliente hacia REDIRECT_ON_FAILURE.

Comentario:
- Se usa salto via HTML/JS porque algunos reverse proxy reescriben Location y terminaban cambiando el host destino.

### 4.2 Retorno con token

Integracion soporta 2 formatos:

1. /mia/auth?token=<JWT>
2. /auth?<JWT> (legacy)

Pasos:

1. Si llega /auth sin basePath, proxy.ts hace rewrite interno a /mia/auth.
2. app/auth/route.ts extrae token desde token= o desde query cruda.
3. Verifica JWT con jose.jwtVerify:
- HS256
- issuer
- audience
- nbf/exp
4. Si valido:
- guarda cookie mia_auth (HttpOnly, SameSite=Lax, Secure segun env)
- redirige a /mia
5. Si invalido o ausente:
- redirige a /mia/auth/failure

## 5. Reglas del proxy (proxy.ts)

### 5.1 Reescrituras de compatibilidad

1. /auth -> rewrite interno a /mia/auth
2. /auth/* -> rewrite interno a /mia/auth/*

Comentario:
- rewrite evita loops de redirect cuando el proxy inverso agrega o quita /mia.

### 5.2 Rutas permitidas sin validar cookie

1. /mia/auth
2. /mia/_next
3. /_next
4. /favicon.ico

Comentario:
- Si se bloqueara /mia/auth, nunca podria entrar un token nuevo.

### 5.3 Cobertura de rutas

matcher actual:

1. /
2. /:path*

Comentario:
- Se intercepta toda la app y luego se excluyen rutas internas.

## 6. Endpoint de fallo (app/auth/failure/route.ts)

Este endpoint:

1. Lee REDIRECT_ON_FAILURE.
2. Valida que sea URL http/https.
3. Si no es valida, usa fallback por defecto.
4. Devuelve HTML con:
- meta refresh
- window.location.replace
- enlace noscript

Comentario:
- Es un mecanismo robusto para escenarios donde Location server-side es manipulado por infraestructura intermedia.

## 7. Seguridad actual

1. Cookie HttpOnly: evita lectura por JS en cliente.
2. SameSite=Lax: reduce riesgo CSRF en navegacion comun.
3. Algoritmo fijo HS256: reduce riesgos de confusion de algoritmo.
4. Validacion de iss y aud: evita reutilizacion de token para otro servicio.

## 8. Riesgos y recomendaciones

1. COOKIE_SECURE=false en produccion
- riesgo: cookie transmitida en HTTP.
- recomendacion: poner COOKIE_SECURE=true cuando haya HTTPS end-to-end.

2. JWT_SECRET en .env.local
- correcto en local, pero no debe versionarse.
- recomendacion: secreto desde vault/secret manager en despliegue.

3. Expiracion de cookie
- actualmente es cookie de sesion (sin maxAge/expires).
- recomendacion: definir maxAge alineado a exp del JWT.

4. Rotacion de secretos
- recomendacion: plan de rotacion periodica con ventana de compatibilidad.

## 9. Troubleshooting (problemas ya vistos)

### 9.1 Entraba a la app sin auth

Causa:
- guard estaba en render y la UI se alcanzaba a montar.

Solucion aplicada:
- mover enforcement al proxy global.

### 9.2 Redirigia a IP local en lugar de grupohemac

Causa:
- reverse proxy reescribiendo Location externo.

Solucion aplicada:
- ruta intermedia /mia/auth/failure que redirige desde HTML cliente.

### 9.3 Error de Next: middleware deprecado / both middleware and proxy

Causa:
- coexistencia o cache stale de middleware.ts.

Solucion aplicada:
1. usar solo proxy.ts
2. eliminar middleware.ts
3. limpiar .next y reiniciar dev server

### 9.4 ERR_TOO_MANY_REDIRECTS

Causa:
- rebotes entre /auth y /mia/auth en presencia de reverse proxy.

Solucion aplicada:
- usar rewrite interno (no redirect) para /auth y /auth/*.

### 9.5 Token llega como /auth?<JWT>

Causa:
- integrador no envia token=.

Solucion aplicada:
- parser de token compatible en app/auth/route.ts.

## 10. Checklist de pruebas funcionales

### 10.1 Sin cookie

1. borrar mia_auth en navegador.
2. abrir /mia.
3. resultado esperado: salida a REDIRECT_ON_FAILURE.

### 10.2 Con token valido

1. abrir /mia/auth?token=<JWT valido> o /auth?<JWT valido>.
2. resultado esperado: crea mia_auth y navega a /mia.

### 10.3 Con token invalido

1. abrir /mia/auth?token=abc.
2. resultado esperado: /mia/auth/failure y salida a REDIRECT_ON_FAILURE.

### 10.4 Auth deshabilitada

1. poner AUTH_ENABLED=false.
2. reiniciar servidor.
3. abrir /mia.
4. resultado esperado: entra directo sin exigir cookie.

## 11. Operacion diaria

1. Despues de cambios en proxy.ts o auth routes:
- reiniciar servidor Next dev.

2. Si aparece comportamiento raro de rutas edge:
- borrar carpeta .next
- reiniciar dev server

## 12. Mejoras futuras sugeridas

1. agregar endpoint de logout (borra cookie mia_auth y redirige).
2. agregar maxAge a cookie segun exp del JWT.
3. registrar eventos de auth (sin loggear token) para auditoria.
4. agregar pruebas automatizadas de rutas de auth con Playwright.

## 13. Referencias internas

1. proxy global: proxy.ts
2. entrada token: app/auth/route.ts
3. salida de fallo: app/auth/failure/route.ts
4. env local: .env.local
