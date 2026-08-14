"use client";

import { useEffect, useRef, useState } from "react";
import { FileInput } from "@/components/FileInput";
import { TaggedDocumentSection } from "./TaggedDocumentSection";
import { downloadProtocolTemplate } from "./templateApi";
import {
  GenerationProgress,
  GenerationProgressView,
} from "@/components/GenerationProgress";
import {
  createC5DocumentJob,
  downloadC5Document,
  generateC5Folders,
  getC5DocumentDiagnostics,
  getC5DocumentJobStatus,
  ProtocolGenerationDiagnostics,
} from "./protocolApi";

const POLLING_INTERVAL_MS = 750;
const MAX_GENERATION_TIME_MS = 60 * 60 * 1000;

type ProtocolWorkspace = "new" | "complete";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function wait(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Operación cancelada.", "AbortError"));
      return;
    }

    const timeoutId = window.setTimeout(() => {
      signal.removeEventListener("abort", handleAbort);
      resolve();
    }, milliseconds);

    function handleAbort() {
      window.clearTimeout(timeoutId);
      reject(new DOMException("Operación cancelada.", "AbortError"));
    }

    signal.addEventListener("abort", handleAbort, { once: true });
  });
}

function ProtocolDiagnosticsCard({
  diagnostics,
}: {
  diagnostics: ProtocolGenerationDiagnostics;
}) {
  const { resumen } = diagnostics;

  const hasObservations =
    resumen.imagenes_no_encontradas > 0 ||
    resumen.imagenes_omitidas_por_dano > 0 ||
    resumen.clasificaciones_no_encontradas > 0;

  if (!hasObservations) {
    return (
      <section className="rounded-4xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-600 text-lg font-black text-white">
            ✓
          </div>

          <div>
            <h3 className="text-base font-bold text-emerald-950">
              Documento generado sin observaciones
            </h3>
            <p className="mt-1 text-sm leading-6 text-emerald-800">
              El documento Word se descargó correctamente y todas las imágenes
              solicitadas pudieron relacionarse con sus carpetas.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-4xl border border-amber-200 bg-white shadow-sm">
      <div className="border-b border-amber-200 bg-amber-50 p-5">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-500 text-lg font-black text-white">
            !
          </div>

          <div>
            <h3 className="text-base font-bold text-amber-950">
              Documento generado con observaciones
            </h3>
            <p className="mt-1 text-sm leading-6 text-amber-900">
              El documento Word se descargó correctamente. Algunas evidencias no
              pudieron encontrarse o insertarse; revisa el detalle antes de
              entregar el documento.
            </p>
          </div>
        </div>
      </div>

      <div className="p-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              Insertadas
            </p>
            <p className="mt-2 text-2xl font-black text-slate-900">
              {resumen.imagenes_insertadas}
            </p>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
              No encontradas
            </p>
            <p className="mt-2 text-2xl font-black text-amber-950">
              {resumen.imagenes_no_encontradas}
            </p>
          </div>

          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-700">
              Omitidas por daño
            </p>
            <p className="mt-2 text-2xl font-black text-rose-950">
              {resumen.imagenes_omitidas_por_dano}
            </p>
          </div>

          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-violet-700">
              Clasificaciones faltantes
            </p>
            <p className="mt-2 text-2xl font-black text-violet-950">
              {resumen.clasificaciones_no_encontradas}
            </p>
          </div>
        </div>

        {diagnostics.imagenes_no_encontradas.length > 0 && (
          <details className="group mt-5 rounded-2xl border border-amber-200 bg-amber-50/60">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-bold text-amber-950">
              <span>
                Ver imágenes no encontradas (
                {diagnostics.imagenes_no_encontradas.length})
              </span>
              <span className="text-lg transition group-open:rotate-180">
                ⌄
              </span>
            </summary>

            <div className="max-h-80 space-y-3 overflow-y-auto border-t border-amber-200 p-4">
              {diagnostics.imagenes_no_encontradas.map((item, index) => (
                <article
                  key={`${item.sitio}-${item.clasificacion}-${item.imagen_solicitada}-${index}`}
                  className="rounded-xl border border-amber-200 bg-white p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold text-slate-900">
                      Imagen solicitada: {item.imagen_solicitada}
                    </p>
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
                      No encontrada
                    </span>
                  </div>

                  <dl className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-800">Sitio</dt>
                      <dd>{item.sitio || "Sin información"}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-800">
                        Clasificación
                      </dt>
                      <dd>{item.clasificacion || "Sin información"}</dd>
                    </div>
                  </dl>

                  <p className="mt-3 text-xs leading-5 text-slate-500">
                    {item.motivo}
                  </p>
                </article>
              ))}
            </div>
          </details>
        )}

        {diagnostics.clasificaciones_no_encontradas.length > 0 && (
          <details className="group mt-4 rounded-2xl border border-violet-200 bg-violet-50/60">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-bold text-violet-950">
              <span>
                Ver clasificaciones no encontradas (
                {diagnostics.clasificaciones_no_encontradas.length})
              </span>
              <span className="text-lg transition group-open:rotate-180">
                ⌄
              </span>
            </summary>

            <div className="max-h-72 space-y-2 overflow-y-auto border-t border-violet-200 p-4">
              {diagnostics.clasificaciones_no_encontradas.map((item, index) => (
                <div
                  key={`${item.sitio}-${item.clasificacion}-${index}`}
                  className="rounded-xl border border-violet-200 bg-white px-4 py-3"
                >
                  <p className="text-sm font-bold text-slate-900">
                    {item.clasificacion}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Sitio: {item.sitio}
                  </p>
                </div>
              ))}
            </div>
          </details>
        )}

        {diagnostics.imagenes_omitidas.length > 0 && (
          <details className="group mt-4 rounded-2xl border border-rose-200 bg-rose-50/60">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-bold text-rose-950">
              <span>
                Ver imágenes omitidas por archivo dañado (
                {diagnostics.imagenes_omitidas.length})
              </span>
              <span className="text-lg transition group-open:rotate-180">
                ⌄
              </span>
            </summary>

            <div className="max-h-72 space-y-2 overflow-y-auto border-t border-rose-200 p-4">
              {diagnostics.imagenes_omitidas.map((item, index) => (
                <div
                  key={`${item.archivo_detectado}-${index}`}
                  className="rounded-xl border border-rose-200 bg-white px-4 py-3"
                >
                  <p className="text-sm font-bold text-slate-900">
                    {item.archivo_detectado}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.sitio} · {item.clasificacion}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-rose-700">
                    {item.motivo}
                  </p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </section>
  );
}


export function ProtocolsSection() {
  const [workspace, setWorkspace] = useState<ProtocolWorkspace>("new");
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [evidenceZip, setEvidenceZip] = useState<File | null>(null);

  const [loadingFolders, setLoadingFolders] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [downloadingSitesTemplate, setDownloadingSitesTemplate] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [diagnostics, setDiagnostics] =
    useState<ProtocolGenerationDiagnostics | null>(null);
  const [documentProgress, setDocumentProgress] =
    useState<GenerationProgressView | null>(null);

  const activeJobController = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      activeJobController.current?.abort();
    };
  }, []);

  async function handleDownloadSitesTemplate() {
    setMessage("");
    setError("");

    try {
      setDownloadingSitesTemplate(true);
      await downloadProtocolTemplate("c5-sites-v1");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible descargar la plantilla oficial.",
      );
    } finally {
      setDownloadingSitesTemplate(false);
    }
  }

  async function handleGenerateFolders() {
    setMessage("");
    setError("");
    setDiagnostics(null);

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
          : "Ocurrió un error generando carpetas.",
      );
    } finally {
      setLoadingFolders(false);
    }
  }

  async function handleGenerateDocument() {
    setMessage("");
    setError("");
    setDiagnostics(null);

    if (!excelFile || !evidenceZip) {
      setError("Selecciona la plantilla Excel y el ZIP de evidencias.");
      return;
    }

    activeJobController.current?.abort();
    const controller = new AbortController();
    activeJobController.current = controller;

    setDocumentProgress({
      status: "uploading",
      stage: "uploading",
      percentage: 2,
      message:
        "Enviando la plantilla Excel y el ZIP de evidencias al servidor.",
      current_site: 0,
      total_sites: 0,
      current_site_name: "",
      processed_images: 0,
      total_images: 0,
      detected_images: 0,
      error: null,
    });

    try {
      setLoadingDocument(true);

      const job = await createC5DocumentJob(
        excelFile,
        evidenceZip,
        controller.signal,
      );

      const startedAt = Date.now();
      let consecutiveStatusErrors = 0;

      while (!controller.signal.aborted) {
        if (Date.now() - startedAt > MAX_GENERATION_TIME_MS) {
          throw new Error(
            "La generación superó el tiempo máximo de espera. Comunícate con el área responsable del sistema.",
          );
        }

        await wait(POLLING_INTERVAL_MS, controller.signal);

        let status;

        try {
          status = await getC5DocumentJobStatus(
            job.job_id,
            controller.signal,
          );
          consecutiveStatusErrors = 0;
        } catch (statusError) {
          if (isAbortError(statusError)) {
            throw statusError;
          }

          consecutiveStatusErrors += 1;

          if (consecutiveStatusErrors >= 4) {
            throw statusError;
          }

          continue;
        }

        setDocumentProgress(status);

        if (status.status === "failed") {
          throw new Error(
            status.error ||
              status.message ||
              "No fue posible generar el documento Word.",
          );
        }

        if (status.status !== "completed") {
          continue;
        }

        await downloadC5Document(job.job_id, controller.signal);

        const resultDiagnostics = status.diagnostics_ready
          ? await getC5DocumentDiagnostics(job.job_id, controller.signal)
          : null;

        setDiagnostics(resultDiagnostics);

        const hasObservations =
          resultDiagnostics !== null &&
          (resultDiagnostics.resumen.imagenes_no_encontradas > 0 ||
            resultDiagnostics.resumen.imagenes_omitidas_por_dano > 0 ||
            resultDiagnostics.resumen.clasificaciones_no_encontradas > 0);

        setMessage(
          hasObservations
            ? "Documento Word generado y descargado. Revisa las observaciones mostradas a continuación."
            : "Documento Word generado y descargado correctamente.",
        );

        break;
      }
    } catch (err) {
      if (isAbortError(err)) {
        return;
      }

      const errorMessage =
        err instanceof Error
          ? err.message
          : "Ocurrió un error generando el documento Word.";

      setError(errorMessage);
      setDocumentProgress((current) =>
        current
          ? {
              ...current,
              status: "failed",
              stage: "failed",
              message: "La generación no pudo completarse.",
              error: errorMessage,
            }
          : null,
      );
    } finally {
      if (activeJobController.current === controller) {
        activeJobController.current = null;
      }
      setLoadingDocument(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-4xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-linear-to-br from-white via-blue-50/70 to-violet-50/60 p-6 md:p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.25em] text-blue-600">
                Protocolos C5
              </p>
              <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
                Automatización documental C5
              </h2>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                Selecciona el proceso que deseas realizar. Cada modo muestra
                únicamente los archivos y acciones necesarios para completar la
                tarea.
              </p>
            </div>

            <div className="inline-flex w-full rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm xl:w-auto">
              <button
                type="button"
                onClick={() => setWorkspace("new")}
                aria-pressed={workspace === "new"}
                className={`flex flex-1 items-center justify-center gap-3 rounded-xl px-4 py-3 text-left transition xl:min-w-60 ${
                  workspace === "new"
                    ? "bg-blue-600 text-white shadow-md"
                    : "text-slate-900 hover:bg-slate-50"
                }`}
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-lg ${
                    workspace === "new" ? "bg-white/15" : "bg-blue-50"
                  }`}
                >
                  ＋
                </span>
                <span>
                  <span className="block text-sm font-black">
                    Crear protocolo nuevo
                  </span>
                  <span
                    className={`mt-0.5 hidden text-xs sm:block ${
                      workspace === "new" ? "text-blue-100" : "text-slate-600"
                    }`}
                  >
                    Excel, carpetas y Word final
                  </span>
                </span>
              </button>

              <button
                type="button"
                onClick={() => setWorkspace("complete")}
                aria-pressed={workspace === "complete"}
                className={`flex flex-1 items-center justify-center gap-3 rounded-xl px-4 py-3 text-left transition xl:min-w-60 ${
                  workspace === "complete"
                    ? "bg-violet-600 text-white shadow-md"
                    : "text-slate-900 hover:bg-slate-50"
                }`}
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-lg ${
                    workspace === "complete" ? "bg-white/15" : "bg-violet-50"
                  }`}
                >
                  ✦
                </span>
                <span>
                  <span className="block text-sm font-black">
                    Completar Word existente
                  </span>
                  <span
                    className={`mt-0.5 hidden text-xs sm:block ${
                      workspace === "complete"
                        ? "text-violet-100"
                        : "text-slate-600"
                    }`}
                  >
                    Agregar secciones con etiquetas
                  </span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {workspace === "new" ? (
        <>
          {error && (
            <section className="rounded-4xl border border-red-200 bg-red-50 p-5 text-sm font-semibold text-red-700 shadow-sm">
              {error}
            </section>
          )}

          {message && (
            <section className="rounded-4xl border border-emerald-200 bg-emerald-50 p-5 text-sm font-semibold text-emerald-700 shadow-sm">
              {message}
            </section>
          )}

          {diagnostics && <ProtocolDiagnosticsCard diagnostics={diagnostics} />}

          <section className="grid gap-6 xl:grid-cols-2">
            <article className="flex flex-col rounded-4xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-start gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-2xl text-white shadow-lg shadow-blue-100">
                  📊
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-600">
                    Paso 1
                  </p>
                  <h3 className="mt-1 text-xl font-black text-slate-950">
                    Preparar estructura
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Descarga la plantilla, captura la información y genera las
                    carpetas donde organizarás las evidencias.
                  </p>
                </div>
              </div>

              <div className="rounded-3xl border border-blue-100 bg-blue-50 p-5">
                <p className="text-sm font-black text-blue-950">
                  Plantilla Excel oficial
                </p>
                <p className="mt-1 text-xs leading-5 text-blue-700">
                  Utiliza este archivo como base y conserva sus columnas y hojas.
                </p>
                <button
                  type="button"
                  onClick={handleDownloadSitesTemplate}
                  disabled={downloadingSitesTemplate}
                  className="mt-4 inline-flex rounded-2xl bg-blue-800 px-4 py-3 text-sm font-black text-white transition hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-blue-600 disabled:text-blue-50"
                >
                  {downloadingSitesTemplate
                    ? "Descargando plantilla..."
                    : "Descargar plantilla Excel"}
                </button>
              </div>

              <div className="mt-5">
                <FileInput
                  label="Subir plantilla Excel"
                  name="excel_file"
                  accept=".xlsx,.xls"
                  required
                  helperText="Archivo Excel con la información de sitios y clasificaciones."
                  onChange={setExcelFile}
                />
              </div>

              <button
                type="button"
                onClick={handleGenerateFolders}
                disabled={loadingFolders}
                className="mt-auto w-full rounded-2xl bg-blue-800 px-6 py-4 pt-4 text-sm font-black text-white shadow-lg transition hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-blue-600 disabled:text-blue-50"
              >
                {loadingFolders
                  ? "Generando estructura..."
                  : "Generar y descargar ZIP"}
              </button>
            </article>

            <article className="flex flex-col rounded-4xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-start gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-2xl text-white shadow-lg shadow-slate-200">
                  📝
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">
                    Paso 2
                  </p>
                  <h3 className="mt-1 text-xl font-black text-slate-950">
                    Generar protocolo
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Sube el ZIP con las evidencias organizadas y genera el Word
                    final con la plantilla oficial del sistema.
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

              {documentProgress && (
                <GenerationProgress progress={documentProgress} />
              )}

              <button
                type="button"
                onClick={handleGenerateDocument}
                disabled={loadingDocument}
                className="mt-auto w-full rounded-2xl bg-slate-900 px-6 py-4 text-sm font-black text-white shadow-lg transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loadingDocument
                  ? `Generando documento... ${documentProgress?.percentage ?? 0}%`
                  : "Generar y descargar documento"}
              </button>
            </article>
          </section>
        </>
      ) : (
        <TaggedDocumentSection />
      )}
    </div>
  );
}


