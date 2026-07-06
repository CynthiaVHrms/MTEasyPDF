"use client";

import { useState } from "react";
import { FileInput } from "@/components/FileInput";
import { generateC5Document, generateC5Folders } from "./protocolApi";

export function ProtocolsSection() {
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [evidenceZip, setEvidenceZip] = useState<File | null>(null);

  const [loadingFolders, setLoadingFolders] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleGenerateFolders() {
    setMessage("");
    setError("");

    if (!excelFile) {
      setError("Selecciona la plantilla Excel para generar las carpetas.");
      return;
    }

    try {
      setLoadingFolders(true);
      await generateC5Folders(excelFile);
      setMessage("Estructura de carpetas generada correctamente.");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Ocurrió un error generando carpetas."
      );
    } finally {
      setLoadingFolders(false);
    }
  }

  async function handleGenerateDocument() {
    setMessage("");
    setError("");

    if (!excelFile || !evidenceZip) {
      setError("Selecciona la plantilla Excel y el ZIP de evidencias.");
      return;
    }

    try {
      setLoadingDocument(true);
      await generateC5Document(excelFile, evidenceZip);
      setMessage("Documento Word generado correctamente.");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Ocurrió un error generando el documento Word."
      );
    } finally {
      setLoadingDocument(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.25em] text-blue-600">
          Protocolos C5
        </p>

        <h2 className="mt-2 text-3xl font-bold text-slate-900">
          Automatización documental C5
        </h2>

        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
          Genera la estructura de carpetas desde una plantilla Excel y después
          crea el documento Word del protocolo utilizando el ZIP de evidencias.
        </p>
      </section>

      {(error || message) && (
        <section
          className={`rounded-[2rem] border p-5 text-sm font-semibold shadow-sm ${
            error
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          }`}
        >
          {error || message}
        </section>
      )}

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-2xl text-white">
              📊
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-900">
                1. Plantilla Excel
              </h3>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Descarga la plantilla, llena la información requerida y súbela
                para generar las carpetas.
              </p>
            </div>
          </div>

          <div className="mb-5 rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <p className="text-sm font-bold text-blue-900">
              Descargar plantilla Excel
            </p>

            <p className="mt-1 text-xs leading-5 text-blue-700">
              Utiliza esta plantilla como base para capturar la información de
              sitios y clasificaciones.
            </p>

            <a
              href="/templates/C5_Información de los sitios_versión_1_0.xlsx"
              download
              className="mt-3 inline-flex rounded-xl bg-blue-700 px-4 py-2 text-sm font-bold text-white transition hover:bg-blue-800"
            >
              Descargar plantilla Excel
            </a>
          </div>

          <FileInput
            label="Subir plantilla Excel"
            name="excel_file"
            accept=".xlsx,.xls"
            required
            helperText="Archivo Excel con la información de sitios y clasificaciones."
            onChange={setExcelFile}
          />

          <button
            type="button"
            onClick={handleGenerateFolders}
            disabled={loadingFolders}
            className="mt-5 w-full rounded-2xl bg-blue-700 px-6 py-4 text-sm font-bold text-white shadow-lg transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loadingFolders
              ? "Generando estructura..."
              : "Descargar ZIP de carpetas"}
          </button>
        </article>

        <article className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800 text-2xl text-white">
              📝
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-900">
                2. Generar documento Word
              </h3>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Sube el ZIP de evidencias y genera el documento final con la
                plantilla oficial configurada en el sistema.
              </p>
            </div>
          </div>

          <FileInput
            label="ZIP de evidencias"
            name="evidence_zip"
            accept=".zip,application/zip,application/x-zip-compressed"
            required
            helperText="ZIP con las evidencias ya organizadas."
            onChange={setEvidenceZip}
          />

          <button
            type="button"
            onClick={handleGenerateDocument}
            disabled={loadingDocument}
            className="mt-5 w-full rounded-2xl bg-slate-800 px-6 py-4 text-sm font-bold text-white shadow-lg transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loadingDocument
              ? "Generando documento Word..."
              : "Descargar documento generado"}
          </button>
        </article>
      </section>
    </div>
  );
}


// "use client";

// import { useState } from "react";
// import { FileInput } from "@/components/FileInput";
// import { generateC5Document, generateC5Folders } from "./protocolApi";

// export function ProtocolsSection() {
//   const [excelFile, setExcelFile] = useState<File | null>(null);
//   const [evidenceZip, setEvidenceZip] = useState<File | null>(null);

//   const [loadingFolders, setLoadingFolders] = useState(false);
//   const [loadingDocument, setLoadingDocument] = useState(false);

//   const [message, setMessage] = useState("");
//   const [error, setError] = useState("");

//   async function handleGenerateFolders() {
//     setMessage("");
//     setError("");

//     if (!excelFile) {
//       setError("Selecciona la plantilla Excel para generar las carpetas.");
//       return;
//     }

//     try {
//       setLoadingFolders(true);
//       await generateC5Folders(excelFile);
//       setMessage("Estructura de carpetas generada correctamente.");
//     } catch (err) {
//       setError(
//         err instanceof Error
//           ? err.message
//           : "Ocurrió un error generando carpetas."
//       );
//     } finally {
//       setLoadingFolders(false);
//     }
//   }

//   async function handleGenerateDocument() {
//     setMessage("");
//     setError("");

//     if (!excelFile || !evidenceZip) {
//       setError("Selecciona la plantilla Excel y el ZIP de evidencias.");
//       return;
//     }

//     try {
//       setLoadingDocument(true);
//       await generateC5Document(excelFile, evidenceZip);
//       setMessage("Documento Word generado correctamente.");
//     } catch (err) {
//       setError(
//         err instanceof Error
//           ? err.message
//           : "Ocurrió un error generando el documento Word."
//       );
//     } finally {
//       setLoadingDocument(false);
//     }
//   }

//   return (
//     <div className="space-y-6">
//       <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
//         <p className="text-xs font-bold uppercase tracking-[0.25em] text-blue-600">
//           Protocolos C5
//         </p>

//         <h2 className="mt-2 text-3xl font-bold text-slate-900">
//           Automatización documental C5
//         </h2>

//         <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
//           Genera la estructura de carpetas desde una plantilla Excel y después
//           crea el documento Word del protocolo utilizando el ZIP de evidencias.
//         </p>
//       </section>

//       {(error || message) && (
//         <section
//           className={`rounded-[2rem] border p-5 text-sm font-semibold shadow-sm ${
//             error
//               ? "border-red-200 bg-red-50 text-red-700"
//               : "border-emerald-200 bg-emerald-50 text-emerald-700"
//           }`}
//         >
//           {error || message}
//         </section>
//       )}

//       <section className="grid gap-6 xl:grid-cols-2">
//         <article className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
//           <div className="mb-6 flex items-start gap-4">
//             <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-2xl text-white">
//               📊
//             </div>

//             <div>
//               <h3 className="text-xl font-bold text-slate-900">
//                 1. Plantilla Excel
//               </h3>
//               <p className="mt-1 text-sm leading-6 text-slate-500">
//                 Sube el Excel acomodado. Este archivo se usará para generar las
//                 carpetas y también para crear el documento Word.
//               </p>
//             </div>
//           </div>

//           <FileInput
//             label="Plantilla Excel"
//             name="excel_file"
//             accept=".xlsx,.xls"
//             required
//             helperText="Archivo Excel con la información de sitios y clasificaciones."
//             onChange={setExcelFile}
//           />

//           <button
//             type="button"
//             onClick={handleGenerateFolders}
//             disabled={loadingFolders}
//             className="mt-5 w-full rounded-2xl bg-blue-700 px-6 py-4 text-sm font-bold text-white shadow-lg transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
//           >
//             {loadingFolders
//               ? "Generando estructura..."
//               : "Descargar ZIP de carpetas"}
//           </button>
//         </article>

//         <article className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
//           <div className="mb-6 flex items-start gap-4">
//             <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800 text-2xl text-white">
//               📝
//             </div>

//             <div>
//               <h3 className="text-xl font-bold text-slate-900">
//                 2. Generar documento Word
//               </h3>
//               <p className="mt-1 text-sm leading-6 text-slate-500">
//                 Sube el ZIP de evidencias y genera el documento final con la
//                 plantilla oficial configurada en el sistema.
//               </p>
//             </div>
//           </div>

//           <FileInput
//             label="ZIP de evidencias"
//             name="evidence_zip"
//             accept=".zip,application/zip,application/x-zip-compressed"
//             required
//             helperText="ZIP con las evidencias ya organizadas."
//             onChange={setEvidenceZip}
//           />

//           <button
//             type="button"
//             onClick={handleGenerateDocument}
//             disabled={loadingDocument}
//             className="mt-5 w-full rounded-2xl bg-slate-800 px-6 py-4 text-sm font-bold text-white shadow-lg transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-slate-400"
//           >
//             {loadingDocument
//               ? "Generando documento Word..."
//               : "Descargar documento generado"}
//           </button>
//         </article>
//       </section>
//     </div>
//   );
// }
