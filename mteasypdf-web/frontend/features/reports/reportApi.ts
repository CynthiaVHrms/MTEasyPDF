import { API_BASE_URL } from "@/features/apiBaseUrl";

export type GenerateReportResponse = {
  job_id: string;
  status: string;
  download_url: string;
  zip_path: string;
};

type CreateReportJobResponse = {
  job_id: string;
  status: "queued";
  status_url: string;
  download_url: string;
};

type ReportJobStatus = {
  status: "queued" | "processing" | "completed" | "failed";
  message: string;
  error: string | null;
  download_ready: boolean;
  zip_path?: string;
};

const REQUEST_TIMEOUT_MS = 30000;
const UPLOAD_REQUEST_TIMEOUT_MS = 0;
const REPORT_POLL_INTERVAL_MS = 2000;
const REPORT_MAX_WAIT_MS = 30 * 60 * 1000;

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timeout =
    timeoutMs > 0
      ? window.setTimeout(() => controller.abort(), timeoutMs)
      : null;

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      if (timeoutMs > 0) {
        throw new Error("El servidor tardó demasiado en responder. Intenta nuevamente.");
      }

      throw new Error("La conexión con el backend se interrumpió antes de completar la carga.");
    }

    throw new Error("No hubo respuesta del backend. Revisa conectividad y URL de API.");
  } finally {
    if (timeout !== null) {
      window.clearTimeout(timeout);
    }
  }
}


export async function generateReport(
  formData: FormData
): Promise<GenerateReportResponse> {
  let job: CreateReportJobResponse;

  try {
    job = await createReportJob(formData);
  } catch (error) {
    if (error instanceof Error && error.message === "__REPORT_JOBS_NOT_AVAILABLE__") {
      return generateReportLegacy(formData);
    }

    throw error;
  }

  const startedAt = Date.now();

  while (true) {
    const currentStatus = await getReportJobStatus(job.job_id);

    if (currentStatus.status === "completed") {
      return {
        job_id: job.job_id,
        status: "completed",
        download_url: job.download_url,
        zip_path: currentStatus.zip_path ?? "",
      };
    }

    if (currentStatus.status === "failed") {
      throw new Error(
        currentStatus.error ||
          currentStatus.message ||
          "No fue posible generar el reporte.",
      );
    }

    if (Date.now() - startedAt > REPORT_MAX_WAIT_MS) {
      throw new Error(
        "La generación sigue en proceso. Vuelve a intentar en unos minutos.",
      );
    }

    await wait(REPORT_POLL_INTERVAL_MS);
  }
}

async function generateReportLegacy(
  formData: FormData,
): Promise<GenerateReportResponse> {
  let response: Response;

  try {
    response = UPLOAD_REQUEST_TIMEOUT_MS <= 0
      ? await fetch(`${API_BASE_URL}/reports/generate`, {
          method: "POST",
          body: formData,
        })
      : await fetchWithTimeout(
          `${API_BASE_URL}/reports/generate`,
          {
            method: "POST",
            body: formData,
          },
          UPLOAD_REQUEST_TIMEOUT_MS,
        );
  } catch {
    throw new Error("No hubo respuesta del backend. Revisa conectividad y URL de API.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 413) {
      throw new Error("El archivo ZIP supera el tamaño permitido por el servidor.");
    }

    const message =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof (data as { detail?: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : "Error generando el reporte.";

    throw new Error(message);
  }

  return data as GenerateReportResponse;
}

async function createReportJob(
  formData: FormData,
): Promise<CreateReportJobResponse> {
  let response: Response;

  try {
    response = UPLOAD_REQUEST_TIMEOUT_MS <= 0
      ? await fetch(`${API_BASE_URL}/reports/jobs`, {
          method: "POST",
          body: formData,
        })
      : await fetchWithTimeout(
          `${API_BASE_URL}/reports/jobs`,
          {
            method: "POST",
            body: formData,
          },
          UPLOAD_REQUEST_TIMEOUT_MS,
        );
  } catch {
    throw new Error("No hubo respuesta del backend. Revisa conectividad y URL de API.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("__REPORT_JOBS_NOT_AVAILABLE__");
    }

    if (response.status === 413) {
      throw new Error("El archivo ZIP supera el tamaño permitido por el servidor.");
    }

    const message =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof (data as { detail?: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : "No fue posible iniciar la generación del reporte.";

    throw new Error(message);
  }

  return data as CreateReportJobResponse;
}

async function getReportJobStatus(jobId: string): Promise<ReportJobStatus> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/reports/${encodeURIComponent(jobId)}/status`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof (payload as { detail?: unknown }).detail === "string"
        ? (payload as { detail: string }).detail
        : "No fue posible consultar el avance del reporte.";

    throw new Error(message);
  }

  return payload as ReportJobStatus;
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function buildDownloadUrl(downloadUrl: string): string {
  return `${API_BASE_URL}${downloadUrl}`;
}