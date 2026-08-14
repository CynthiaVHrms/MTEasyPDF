import { API_BASE_URL } from "@/features/apiBaseUrl";

export type GenerateReportResponse = {
  job_id: string;
  status: string;
  download_url: string;
  zip_path: string;
};

const REQUEST_TIMEOUT_MS = 30000;

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("El servidor tardó demasiado en responder. Intenta nuevamente.");
    }

    throw new Error("No hubo respuesta del backend. Revisa conectividad y URL de API.");
  } finally {
    window.clearTimeout(timeout);
  }
}


export async function generateReport(
  formData: FormData
): Promise<GenerateReportResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/reports/generate`, {
    method: "POST",
    body: formData,
  });

  let data: unknown;

  try {
    data = await response.json();
  } catch {
    throw new Error("El servidor respondió con un formato inválido.");
  }

  if (!response.ok) {
    const message =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof data.detail === "string"
        ? data.detail
        : "Error generando el reporte.";

    throw new Error(message);
  }

  return data as GenerateReportResponse;
}

export function buildDownloadUrl(downloadUrl: string): string {
  return `${API_BASE_URL}${downloadUrl}`;
}