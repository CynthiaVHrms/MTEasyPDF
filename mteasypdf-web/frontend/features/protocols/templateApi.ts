const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://10.241.1.8:8001";

export type ProtocolTemplateId = "c5-sites-v1" | "c5-tags-v1";

const DOWNLOAD_FILENAMES: Record<ProtocolTemplateId, string> = {
  "c5-sites-v1": "C5_Información_de_los_sitios_versión_1_0.xlsx",
  "c5-tags-v1": "C5_Etiquetas_Word_v1.xlsx",
};

async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload: unknown = await response.json().catch(() => null);

  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof (payload as { detail?: unknown }).detail === "string"
  ) {
    return (payload as { detail: string }).detail;
  }

  return fallback;
}

function downloadBlob(blob: Blob, filename: string): void {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(objectUrl);
}

export async function downloadProtocolTemplate(
  templateId: ProtocolTemplateId,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/protocols/templates/${templateId}/download`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        "No fue posible descargar la plantilla oficial.",
      ),
    );
  }

  const blob = await response.blob();
  downloadBlob(blob, DOWNLOAD_FILENAMES[templateId]);
}