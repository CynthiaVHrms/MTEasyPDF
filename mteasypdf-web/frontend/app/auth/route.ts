/**
 * route.ts — Endpoint de entrada de autenticación para MIA.
 *
 * Herramientas Conexión redirige al usuario hacia este endpoint
 * incluyendo el JWT en el query param `token`:
 *
 *   http://<host>/mia/auth?token=<JWT>
 *
 * Flujo:
 *   1. Se lee el token del query string.
 *   2. Se valida firma, iss, aud, nbf y exp con la librería `jose`.
 *   3. Si el token es válido:
 *        - Se guarda en la cookie HttpOnly `mia_auth`.
 *        - Se redirige al usuario a /mia (URL limpia, sin token visible).
 *   4. Si el token es inválido o no está presente:
 *        - Se redirige a REDIRECT_ON_FAILURE (Herramientas Conexión).
 *
 * Variables de entorno requeridas (en .env.local):
 *   AUTH_ENABLED        — 'false' para saltarse la validación (modo debug)
 *   JWT_SECRET          — Secreto compartido con Herramientas Conexión
 *   JWT_ISSUER          — Valor esperado del claim 'iss'
 *   JWT_AUDIENCE        — Valor esperado del claim 'aud'
 *   REDIRECT_ON_FAILURE — URL de HC a la que redirigir si el token es inválido
 *   COOKIE_SECURE       — 'true' cuando haya HTTPS disponible
 *
 * Nota: Este módulo corre únicamente en el servidor de Next.js.
 * El secreto JWT nunca llega al navegador.
 */

import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

function getFailureRedirectUrl(request: NextRequest): URL {
  return new URL("/mia/auth/failure", request.url);
}

function getClockToleranceSeconds(): number {
  const raw = process.env.JWT_CLOCK_TOLERANCE_SEC?.trim();
  const parsed = Number(raw);

  if (!Number.isFinite(parsed) || parsed < 0) {
    return 15;
  }

  return parsed;
}

function getTokenFromRequest(request: NextRequest): string | null {
  const tokenParam = request.nextUrl.searchParams.get("token")?.trim();
  if (tokenParam) {
    return tokenParam;
  }

  // Compatibilidad: algunos emisores mandan /auth?<JWT> en lugar de /auth?token=<JWT>
  const rawSearch = request.nextUrl.search.startsWith("?")
    ? request.nextUrl.search.slice(1)
    : request.nextUrl.search;

  if (!rawSearch) {
    return null;
  }

  const firstPart = rawSearch.split("&")[0]?.trim();
  if (!firstPart) {
    return null;
  }

  const decoded = decodeURIComponent(firstPart);
  return decoded.includes(".") ? decoded : null;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const authEnabled = process.env.AUTH_ENABLED !== "false";
  const redirectOnFailure = getFailureRedirectUrl(request);
  const clockTolerance = getClockToleranceSeconds();

  // Modo debug: auth desactivada, pasar directo a la aplicación
  if (!authEnabled) {
    const baseUrl = `${request.nextUrl.protocol}//${request.nextUrl.host}`;
    return NextResponse.redirect(new URL("/mia", baseUrl));
  }

  const token = getTokenFromRequest(request);

  // Sin token en la URL — redirigir a Herramientas Conexión
  if (!token) {
    console.warn("[auth] Missing token in /mia/auth request");
    return NextResponse.redirect(redirectOnFailure);
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET ?? "");

    // Verificar firma, algoritmo, iss, aud, nbf y exp
    await jwtVerify(token, secret, {
      issuer: process.env.JWT_ISSUER ?? "suricato",
      audience: process.env.JWT_AUDIENCE ?? "mia",
      algorithms: ["HS256"], // Solo HS256 permitido — protege contra algorithm confusion
      clockTolerance,
    });

    const baseUrl = `${request.nextUrl.protocol}//${request.nextUrl.host}`;
    const response = NextResponse.redirect(new URL("/mia", baseUrl));

    // Sacar el token de la URL guardándolo en una cookie HttpOnly.
    // HttpOnly impide que JavaScript del cliente acceda al token.
    // COOKIE_SECURE debe ser true en producción (HTTPS).
    const cookieSecure = process.env.COOKIE_SECURE === "true";
    response.cookies.set("mia_auth", token, {
      httpOnly: true,
      sameSite: "lax",
      secure: cookieSecure,
      path: "/",
    });

    return response;
  } catch (error) {
    // Token inválido, expirado o con claims incorrectos
    console.warn("[auth] Token validation failed:", error);
    return NextResponse.redirect(redirectOnFailure);
  }
}
