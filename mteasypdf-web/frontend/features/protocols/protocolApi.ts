const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

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

export async function generateC5Folders(excelFile: File) {
  const formData = new FormData();
  formData.append("excel_file", excelFile);

  const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Error generando carpetas.");
  }

  const blob = await response.blob();
  downloadBlob(blob, "Estructura_Carpetas_C5.zip");
}

export async function generateC5Document(excelFile: File, evidenceZip: File) {
  const formData = new FormData();

  formData.append("excel_file", excelFile);
  formData.append("evidence_zip", evidenceZip);

  const response = await fetch(`${API_BASE_URL}/protocols/document/generate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Error generando documento Word.");
  }

  const blob = await response.blob();
  downloadBlob(blob, "Protocolo_C5_Generado.docx");
}



// const API_BASE_URL =
//   process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
//   "http://127.0.0.1:8000";

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


// export async function generateC5Folders(excelFile: File) {
//   const formData = new FormData();
//   formData.append("excel_file", excelFile);

//   const response = await fetch(`${API_BASE_URL}/protocols/folders/generate`, {
//     method: "POST",
//     body: formData,
//   });

//   if (!response.ok) {
//     const error = await response.json().catch(() => null);
//     throw new Error(error?.detail ?? "Error generando carpetas.");
//   }

//   const blob = await response.blob();
//   downloadBlob(blob, "Estructura_Carpetas_C5.zip");
// }

// export async function generateC5Document(
//   excelFile: File,
//   evidenceZip: File,
//   templateDocx: File
// ) {
//   const formData = new FormData();

//   formData.append("excel_file", excelFile);
//   formData.append("evidence_zip", evidenceZip);
//   formData.append("template_docx", templateDocx);

//   const response = await fetch(`${API_BASE_URL}/protocols/document/generate`, {
//     method: "POST",
//     body: formData,
//   });

//   if (!response.ok) {
//     const error = await response.json().catch(() => null);
//     throw new Error(error?.detail ?? "Error generando documento Word.");
//   }

//   const blob = await response.blob();
//   downloadBlob(blob, "Protocolo_C5_Generado.docx");
// }