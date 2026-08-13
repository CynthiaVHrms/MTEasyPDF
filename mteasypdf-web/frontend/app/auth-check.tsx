/**
 * auth-check.tsx — Componente servidor que verifica la sesión.
 *
 * Corre SOLO en el servidor, antes de renderizar la página.
 * Si no hay sesión válida, devuelve RedirectExternal que hace
 * la redirección cross-origin en el cliente.
 *
 * Nota: No se usa redirect() de next/navigation para URLs externas porque
 * Next.js 16 en Server Components extrae solo el pathname y lo resuelve
 * contra el host actual, ignorando el origen de la URL destino.
 */

import { cookies } from "next/headers";
import { jwtVerify } from "jose";
import { RedirectExternal } from "@/components/RedirectExternal";

export async function AuthCheck(): Promise<React.ReactNode> {
  const authEnabled = process.env.AUTH_ENABLED !== "false";

  // Modo debug: auth desactivada
  if (!authEnabled) {
    return null;
  }

  const cookieStore = await cookies();
  const token = cookieStore.get("mia_auth")?.value;
  const redirectOnFailure = process.env.REDIRECT_ON_FAILURE ?? "http://localhost";

  // Sin cookie — redirigir a Herramientas Conexión
  if (!token) {
    return <RedirectExternal url={redirectOnFailure} />;
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
    // Token inválido o expirado — redirigir a Herramientas Conexión
    return <RedirectExternal url={redirectOnFailure} />;
  }
}
