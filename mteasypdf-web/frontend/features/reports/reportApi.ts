export type GenerateReportResponse = {
  job_id: string;
  status: string;
  download_url: string;
  zip_path: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function generateReport(
  formData: FormData
): Promise<GenerateReportResponse> {
  const response = await fetch(`${API_BASE_URL}/reports/generate`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail ?? "Error generando el reporte.");
  }

  return data;
}

export function buildDownloadUrl(downloadUrl: string): string {
  return `${API_BASE_URL}${downloadUrl}`;
}