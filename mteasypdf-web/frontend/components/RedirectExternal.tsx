"use client";

import { useEffect } from "react";

/**
 * RedirectExternal — Client Component para redirección a URLs externas.
 *
 * Se usa cuando un Server Component necesita redirigir a una URL
 * de otro dominio/origen. `redirect()` de next/navigation en Next.js 16
 * no maneja correctamente redirects cross-origin en Server Components —
 * extrae solo el pathname y lo resuelve contra el host actual.
 *
 * Este componente se renderiza en el cliente e inmediatamente redirige
 * via window.location.replace (sin dejar historial de navegación).
 */
export function RedirectExternal({ url }: { url: string }) {
  useEffect(() => {
    window.location.replace(url);
  }, [url]);

  // Renderiza null para no mostrar contenido durante el breve instante
  // antes de que el browser ejecute la redirección
  return null;
}
