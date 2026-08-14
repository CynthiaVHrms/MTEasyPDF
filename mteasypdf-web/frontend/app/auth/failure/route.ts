import { NextRequest, NextResponse } from "next/server";

const DEFAULT_REDIRECT_ON_FAILURE =
  "https://app.grupohemac.com.mx:3003/select-platform";

function resolveRedirectOnFailure(): string {
  const raw = process.env.REDIRECT_ON_FAILURE?.trim();
  if (!raw) {
    return DEFAULT_REDIRECT_ON_FAILURE;
  }

  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return DEFAULT_REDIRECT_ON_FAILURE;
    }

    return parsed.toString();
  } catch {
    return DEFAULT_REDIRECT_ON_FAILURE;
  }
}

export async function GET(_request: NextRequest): Promise<NextResponse> {
  const target = resolveRedirectOnFailure();

  const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta http-equiv="refresh" content="0;url=${target}" />
  <title>Redirigiendo...</title>
</head>
<body>
  <script>
    window.location.replace(${JSON.stringify(target)});
  </script>
  <noscript>
    <a href="${target}">Continuar</a>
  </noscript>
</body>
</html>`;

  return new NextResponse(html, {
    status: 200,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store, no-cache, must-revalidate, proxy-revalidate",
    },
  });
}
