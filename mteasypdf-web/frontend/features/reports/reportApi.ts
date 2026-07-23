export type GenerateReportResponse = {
  job_id: string;
  status: string;
  download_url: string;
  zip_path: string;
};


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://10.241.1.8:8001";


export async function generateReport(
  formData: FormData
): Promise<GenerateReportResponse> {
  const response = await fetch(`${API_BASE_URL}/reports/generate`, {
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