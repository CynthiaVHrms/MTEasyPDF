const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://10.241.1.8:8003";

export type MissingImageDiagnostic = {
  sitio: string;
  clasificacion: string;
  imagen_solicitada: string;
  enlace: string;
  motivo: string;
};

export type OmittedImageDiagnostic = {
  sitio: string;
  clasificacion: string;
  imagen_solicitada: string;
  archivo_detectado: string;
  motivo: string;
};

export type MissingClassificationDiagnostic = {
  sitio: string;
  clasificacion: string;
  enlace: string;
};

export type ProtocolDiagnosticsSummary = {
  imagenes_detectadas_en_zip: number;
  imagenes_insertadas: number;
  imagenes_no_encontradas: number;
  imagenes_omitidas_por_dano: number;
  clasificaciones_no_encontradas: number;
};

export type ProtocolGenerationDiagnostics = {
  schema_version: string;
  job_id: string;
  estado: "completado" | "completado_con_observaciones";
  resumen: ProtocolDiagnosticsSummary;
  imagenes_no_encontradas: MissingImageDiagnostic[];
  imagenes_omitidas: OmittedImageDiagnostic[];
  clasificaciones_no_encontradas: MissingClassificationDiagnostic[];
};

export type ProtocolDocumentJobStatus = {
  schema_version: string;
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: string;
  percentage: number;
  message: string;
  current_site: number;
  total_sites: number;
  current_site_name: string;
  processed_images: number;
  total_images: number;
  detected_images: number;
  download_ready: boolean;
  diagnostics_ready: boolean;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateProtocolDocumentJobResponse = {
  job_id: string;
  status: "queued";
  status_url: string;
  download_url: string;
  diagnostics_url: string;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  link.remove();
  window.URL.revokeObjectURL(url);
}

async function getErrorMessage(
  response: Response,
  fallbackMessage: string,
): Promise<string> {
  const errorPayload = await response.json().catch(() => null);

  if (
    typeof errorPayload === "object" &&
    errorPayload !== null &&
    "detail" in errorPayload &&
    typeof errorPayload.detail === "string"
  ) {
    return errorPayload.detail;
  }

  return fallbackMessage;
}

export async function generateC5Folders(excelFile: File): Promise<void> {
  const formData = new FormData();
  formData.append("excel_file", excelFile);

  const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Error generando carpetas."),
    );
  }

  const blob = await response.blob();
  downloadBlob(blob, "Estructura_Carpetas_C5.zip");
}

export async function createC5DocumentJob(
  excelFile: File,
  evidenceZip: File,
  signal?: AbortSignal,
): Promise<CreateProtocolDocumentJobResponse> {
  const formData = new FormData();

  formData.append("excel_file", excelFile);
  formData.append("evidence_zip", evidenceZip);

  const response = await fetch(`${API_BASE_URL}/protocols/document/jobs`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "No fue posible iniciar la generación del documento Word.",
      ),
    );
  }

  return (await response.json()) as CreateProtocolDocumentJobResponse;
}

export async function getC5DocumentJobStatus(
  jobId: string,
  signal?: AbortSignal,
): Promise<ProtocolDocumentJobStatus> {
  const response = await fetch(
    `${API_BASE_URL}/protocols/document/${encodeURIComponent(jobId)}/status`,
    {
      method: "GET",
      cache: "no-store",
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "No fue posible consultar el avance de la generación.",
      ),
    );
  }

  return (await response.json()) as ProtocolDocumentJobStatus;
}

export async function downloadC5Document(
  jobId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/protocols/document/${encodeURIComponent(jobId)}/download`,
    {
      method: "GET",
      cache: "no-store",
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "El documento terminó, pero no fue posible descargarlo.",
      ),
    );
  }

  const blob = await response.blob();
  downloadBlob(blob, "Protocolo_C5_Generado.docx");
}

export async function getC5DocumentDiagnostics(
  jobId: string,
  signal?: AbortSignal,
): Promise<ProtocolGenerationDiagnostics | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/protocols/document/${encodeURIComponent(
        jobId,
      )}/diagnostics`,
      {
        method: "GET",
        cache: "no-store",
        signal,
      },
    );

    if (!response.ok) {
      console.warn(
        "No fue posible consultar el diagnóstico del documento:",
        response.status,
      );
      return null;
    }

    return (await response.json()) as ProtocolGenerationDiagnostics;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }

    console.warn(
      "El documento se descargó, pero no fue posible consultar su diagnóstico.",
      error,
    );
    return null;
  }
}











// const API_BASE_URL =
//   process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
//   "http://10.241.1.8:8000";

// export type MissingImageDiagnostic = {
//   sitio: string;
//   clasificacion: string;
//   imagen_solicitada: string;
//   enlace: string;
//   motivo: string;
// };

// export type OmittedImageDiagnostic = {
//   sitio: string;
//   clasificacion: string;
//   imagen_solicitada: string;
//   archivo_detectado: string;
//   motivo: string;
// };

// export type MissingClassificationDiagnostic = {
//   sitio: string;
//   clasificacion: string;
//   enlace: string;
// };

// export type ProtocolDiagnosticsSummary = {
//   imagenes_detectadas_en_zip: number;
//   imagenes_insertadas: number;
//   imagenes_no_encontradas: number;
//   imagenes_omitidas_por_dano: number;
//   clasificaciones_no_encontradas: number;
// };

// export type ProtocolGenerationDiagnostics = {
//   schema_version: string;
//   job_id: string;
//   estado: "completado" | "completado_con_observaciones";
//   resumen: ProtocolDiagnosticsSummary;
//   imagenes_no_encontradas: MissingImageDiagnostic[];
//   imagenes_omitidas: OmittedImageDiagnostic[];
//   clasificaciones_no_encontradas: MissingClassificationDiagnostic[];
// };

// export type GenerateC5DocumentResult = {
//   jobId: string | null;
//   diagnostics: ProtocolGenerationDiagnostics | null;
// };

// function downloadBlob(blob: Blob, filename: string) {
//   const url = window.URL.createObjectURL(blob);
//   const link = document.createElement("a");

//   link.href = url;
//   link.download = filename;
//   document.body.appendChild(link);
//   link.click();

//   link.remove();
//   window.URL.revokeObjectURL(url);
// }

// async function getErrorMessage(
//   response: Response,
//   fallbackMessage: string,
// ): Promise<string> {
//   const errorPayload = await response.json().catch(() => null);

//   if (
//     typeof errorPayload === "object" &&
//     errorPayload !== null &&
//     "detail" in errorPayload &&
//     typeof errorPayload.detail === "string"
//   ) {
//     return errorPayload.detail;
//   }

//   return fallbackMessage;
// }

// async function getDocumentDiagnostics(
//   jobId: string,
// ): Promise<ProtocolGenerationDiagnostics | null> {
//   try {
//     const response = await fetch(
//       `${API_BASE_URL}/protocols/document/${encodeURIComponent(
//         jobId,
//       )}/diagnostics`,
//       {
//         method: "GET",
//         cache: "no-store",
//       },
//     );

//     if (!response.ok) {
//       console.warn(
//         "No fue posible consultar el diagnóstico del documento:",
//         response.status,
//       );
//       return null;
//     }

//     return (await response.json()) as ProtocolGenerationDiagnostics;
//   } catch (error) {
//     console.warn(
//       "El documento se descargó, pero no fue posible consultar su diagnóstico.",
//       error,
//     );
//     return null;
//   }
// }

// export async function generateC5Folders(excelFile: File): Promise<void> {
//   const formData = new FormData();
//   formData.append("excel_file", excelFile);

//   const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
//     method: "POST",
//     body: formData,
//   });

//   if (!response.ok) {
//     throw new Error(
//       await getErrorMessage(response, "Error generando carpetas."),
//     );
//   }

//   const blob = await response.blob();
//   downloadBlob(blob, "Estructura_Carpetas_C5.zip");
// }

// export async function generateC5Document(
//   excelFile: File,
//   evidenceZip: File,
// ): Promise<GenerateC5DocumentResult> {
//   const formData = new FormData();

//   formData.append("excel_file", excelFile);
//   formData.append("evidence_zip", evidenceZip);

//   const response = await fetch(`${API_BASE_URL}/protocols/document/generate`, {
//     method: "POST",
//     body: formData,
//   });

//   if (!response.ok) {
//     throw new Error(
//       await getErrorMessage(response, "Error generando documento Word."),
//     );
//   }

//   const jobId = response.headers.get("X-Job-Id");
//   const blob = await response.blob();

//   downloadBlob(blob, "Protocolo_C5_Generado.docx");

//   const diagnostics = jobId ? await getDocumentDiagnostics(jobId) : null;

//   return {
//     jobId,
//     diagnostics,
//   };
// }
























// // const API_BASE_URL =
// //   process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
// //   "http://10.241.1.8:8000";

// // function downloadBlob(blob: Blob, filename: string) {
// //   const url = window.URL.createObjectURL(blob);
// //   const link = document.createElement("a");

// //   link.href = url;
// //   link.download = filename;
// //   document.body.appendChild(link);
// //   link.click();

// //   link.remove();
// //   window.URL.revokeObjectURL(url);
// // }

// // export async function generateC5Folders(excelFile: File) {
// //   const formData = new FormData();
// //   formData.append("excel_file", excelFile);

// //   const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
// //     method: "POST",
// //     body: formData,
// //   });

// //   if (!response.ok) {
// //     const error = await response.json().catch(() => null);
// //     throw new Error(error?.detail ?? "Error generando carpetas.");
// //   }

// //   const blob = await response.blob();
// //   downloadBlob(blob, "Estructura_Carpetas_C5.zip");
// // }

// // export async function generateC5Document(excelFile: File, evidenceZip: File) {
// //   const formData = new FormData();

// //   formData.append("excel_file", excelFile);
// //   formData.append("evidence_zip", evidenceZip);

// //   const response = await fetch(`${API_BASE_URL}/protocols/document/generate`, {
// //     method: "POST",
// //     body: formData,
// //   });

// //   if (!response.ok) {
// //     const error = await response.json().catch(() => null);
// //     throw new Error(error?.detail ?? "Error generando documento Word.");
// //   }

// //   const blob = await response.blob();
// //   downloadBlob(blob, "Protocolo_C5_Generado.docx");
// // }



// // // const API_BASE_URL =
// // //   process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
// // //   "http://127.0.0.1:8000";

// // // function downloadBlob(blob: Blob, filename: string) {
// // //   const url = window.URL.createObjectURL(blob);
// // //   const link = document.createElement("a");

// // //   link.href = url;
// // //   link.download = filename;
// // //   document.body.appendChild(link);
// // //   link.click();

// // //   link.remove();
// // //   window.URL.revokeObjectURL(url);
// // // }


// // // export async function generateC5Folders(excelFile: File) {
// // //   const formData = new FormData();
// // //   formData.append("excel_file", excelFile);

// // //   const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
// // //     method: "POST",
// // //     body: formData,
// // //   });

// // //   if (!response.ok) {
// // //     const error = await response.json().catch(() => null);
// // //     throw new Error(error?.detail ?? "Error generando carpetas.");
// // //   }

// // //   const blob = await response.blob();
// // //   downloadBlob(blob, "Estructura_Carpetas_C5.zip");
// // // }

// // // export async function generateC5Document(
// // //   excelFile: File,
// // //   evidenceZip: File,
// // //   templateDocx: File
// // // ) {
// // //   const formData = new FormData();

// // //   formData.append("excel_file", excelFile);
// // //   formData.append("evidence_zip", evidenceZip);
// // //   formData.append("template_docx", templateDocx);

// // //   const response = await fetch(`${API_BASE_URL}/protocols/document/generate`, {
// // //     method: "POST",
// // //     body: formData,
// // //   });

// // //   if (!response.ok) {
// // //     const error = await response.json().catch(() => null);
// // //     throw new Error(error?.detail ?? "Error generando documento Word.");
// // //   }

// // //   const blob = await response.blob();
// // //   downloadBlob(blob, "Protocolo_C5_Generado.docx");
// // // }
