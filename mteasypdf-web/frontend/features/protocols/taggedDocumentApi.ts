const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://10.241.1.8:8001";


export type DuplicateWordTag = {
  tag: string;
  occurrences: number;
};

export type TaggedDocumentValidation = {
  request_id?: string;
  compatible: boolean;
  word_tags: string[];
  excel_tags: string[];
  matched_tags: string[];
  missing_in_word: string[];
  missing_in_excel: string[];
  duplicated_in_word: DuplicateWordTag[];
  generic_pending_texts: string[];
  total_word_tags: number;
  total_excel_tags: number;
  total_matches: number;
};

type ValidationErrorPayload = {
  message?: string;
  validation?: TaggedDocumentValidation;
};

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

async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload: unknown = await response.json().catch(() => null);

  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload
  ) {
    const detail = (
      payload as {
        detail?: string | ValidationErrorPayload;
      }
    ).detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (
      typeof detail === "object" &&
      detail !== null &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
  }

  return fallback;
}

export async function validateTaggedDocument(
  excelFile: File,
  wordFile: File,
): Promise<TaggedDocumentValidation> {
  const formData = new FormData();
  formData.append("excel_file", excelFile);
  formData.append("tagged_document", wordFile);

  const response = await fetch(
    `${API_BASE_URL}/protocols/document-tags-v2/validate`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        "No fue posible validar las etiquetas del Word y del Excel.",
      ),
    );
  }

  return (await response.json()) as TaggedDocumentValidation;
}

export async function generateTaggedFolders(
  excelFile: File,
): Promise<void> {
  const formData = new FormData();
  formData.append("excel_file", excelFile);

  const response = await fetch(
    `${API_BASE_URL}/protocols/document-tags-v2/folders/generate`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        "No fue posible generar la estructura de carpetas.",
      ),
    );
  }

  const blob = await response.blob();
  downloadBlob(blob, "Estructura_Etiquetas_Word.zip");
}

export async function generateValidatedTaggedDocument(
  excelFile: File,
  wordFile: File,
  evidenceZip: File,
): Promise<TaggedDocumentGenerationResult> {
  const formData = new FormData();
  formData.append("excel_file", excelFile);
  formData.append("tagged_document", wordFile);
  formData.append("evidence_zip", evidenceZip);

  const response = await fetch(
    `${API_BASE_URL}/protocols/document-tags-v2/generate`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        "No fue posible completar el documento Word.",
      ),
    );
  }

  const jobId = response.headers.get("X-Job-Id") ?? "";
  const blob = await response.blob();
  downloadBlob(blob, "Documento_Completo_Etiquetas.docx");

  if (!jobId) {
    throw new Error(
      "El documento se descargó, pero el servidor no devolvió el identificador necesario para consultar el diagnóstico.",
    );
  }

  const diagnosticsResponse = await fetch(
    `${API_BASE_URL}/protocols/document-tags-v2/${jobId}/diagnostics`,
    { method: "GET" },
  );

  if (!diagnosticsResponse.ok) {
    throw new Error(
      await readApiError(
        diagnosticsResponse,
        "El documento se descargó, pero no fue posible consultar sus observaciones.",
      ),
    );
  }

  return {
    jobId,
    diagnostics: (await diagnosticsResponse.json()) as TaggedDocumentDiagnostics,
  };
}

export type TaggedDocumentDiagnostics = import("@/components/DocumentDiagnostics").DocumentDiagnosticsData;

export type TaggedDocumentGenerationResult = {
  jobId: string;
  diagnostics: TaggedDocumentDiagnostics;
};




// const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
//   "http://10.241.1.8:8003";


// export type DuplicateWordTag = {
//   tag: string;
//   occurrences: number;
// };


// export type TaggedDocumentValidation = {
//   request_id?: string;
//   compatible: boolean;

//   word_tags: string[];
//   excel_tags: string[];
//   matched_tags: string[];

//   missing_in_word: string[];
//   missing_in_excel: string[];

//   duplicated_in_word: DuplicateWordTag[];

//   generic_pending_texts: string[];

//   total_word_tags: number;
//   total_excel_tags: number;
//   total_matches: number;
// };


// type ValidationErrorPayload = {
//   message?: string;
//   validation?: TaggedDocumentValidation;
// };


// function downloadBlob(
//   blob: Blob,
//   filename: string,
// ): void {
//   const objectUrl = window.URL.createObjectURL(blob);
//   const link = document.createElement("a");

//   link.href = objectUrl;
//   link.download = filename;

//   document.body.appendChild(link);
//   link.click();
//   link.remove();

//   window.URL.revokeObjectURL(objectUrl);
// }


// async function readApiError(
//   response: Response,
//   fallback: string,
// ): Promise<string> {
//   const payload: unknown = await response
//     .json()
//     .catch(() => null);

//   if (
//     typeof payload === "object" &&
//     payload !== null &&
//     "detail" in payload
//   ) {
//     const detail = (
//       payload as {
//         detail?: string | ValidationErrorPayload;
//       }
//     ).detail;

//     if (typeof detail === "string") {
//       return detail;
//     }

//     if (
//       typeof detail === "object" &&
//       detail !== null &&
//       typeof detail.message === "string"
//     ) {
//       return detail.message;
//     }
//   }

//   return fallback;
// }


// export async function validateTaggedDocument(
//   excelFile: File,
//   wordFile: File,
// ): Promise<TaggedDocumentValidation> {
//   const formData = new FormData();

//   formData.append("excel_file", excelFile);
//   formData.append("tagged_document", wordFile);

//   const response = await fetch(
//     `${API_BASE_URL}/protocols/document-tags-v2/validate`,
//     {
//       method: "POST",
//       body: formData,
//     },
//   );

//   if (!response.ok) {
//     throw new Error(
//       await readApiError(
//         response,
//         "No fue posible validar las etiquetas del Word y del Excel.",
//       ),
//     );
//   }

//   return (
//     await response.json()
//   ) as TaggedDocumentValidation;
// }


// export async function generateTaggedFolders(
//   excelFile: File,
// ): Promise<void> {
//   const formData = new FormData();

//   formData.append("excel_file", excelFile);

//   const response = await fetch(
//     `${API_BASE_URL}/protocols/document-tags-v2/folders/generate`,
//     {
//       method: "POST",
//       body: formData,
//     },
//   );

//   if (!response.ok) {
//     throw new Error(
//       await readApiError(
//         response,
//         "No fue posible generar la estructura de carpetas.",
//       ),
//     );
//   }

//   const blob = await response.blob();

//   downloadBlob(
//     blob,
//     "Estructura_Etiquetas_Word.zip",
//   );
// }


// export async function generateValidatedTaggedDocument(
//   excelFile: File,
//   wordFile: File,
//   evidenceZip: File,
// ): Promise<void> {
//   const formData = new FormData();

//   formData.append("excel_file", excelFile);
//   formData.append("tagged_document", wordFile);
//   formData.append("evidence_zip", evidenceZip);

//   const response = await fetch(
//     `${API_BASE_URL}/protocols/document-tags-v2/generate`,
//     {
//       method: "POST",
//       body: formData,
//     },
//   );

//   if (!response.ok) {
//     throw new Error(
//       await readApiError(
//         response,
//         "No fue posible completar el documento Word.",
//       ),
//     );
//   }

//   const blob = await response.blob();

//   downloadBlob(
//     blob,
//     "Documento_Completo_Etiquetas.docx",
//   );
// }