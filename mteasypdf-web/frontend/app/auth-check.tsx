/**
 * auth-check.tsx — Componente servidor que verifica la sesión.
 *
 * Corre SOLO en el servidor, antes de renderizar la página.
 * Si no hay sesión válida, redirige a REDIRECT_ON_FAILURE.
 *
 * Uso: importar y usar en el layout root o en páginas protegidas.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { jwtVerify } from "jose";

export async function AuthCheck(): Promise<null> {
  const authEnabled = process.env.AUTH_ENABLED !== "false";

  // Modo debug: auth desactivada
  if (!authEnabled) {
    return null;
  }

  const cookieStore = await cookies();
  const token = cookieStore.get("mia_auth")?.value;
  const redirectOnFailure = process.env.REDIRECT_ON_FAILURE ?? "http://localhost";

  // Sin cookie o cookie vacía
  if (!token) {
    redirect(redirectOnFailure);
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET ?? "");

    await jwtVerify(token, secret, {
      issuer: process.env.JWT_ISSUER ?? "suricato",
      audience: process.env.JWT_AUDIENCE ?? "mia",
      algorithms: ["HS256"],
    });

    return null;
  } catch {
    // Token inválido o expirado
    redirect(redirectOnFailure);
  }
}
