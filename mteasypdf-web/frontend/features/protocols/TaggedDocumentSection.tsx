"use client";

import { useState } from "react";
import { FileInput } from "@/components/FileInput";
import { DocumentDiagnostics } from "@/components/DocumentDiagnostics";
import type { DocumentDiagnosticsData } from "@/components/DocumentDiagnostics";
import {
  generateTaggedFolders,
  generateValidatedTaggedDocument,
  TaggedDocumentValidation,
  validateTaggedDocument,
} from "./taggedDocumentApi";
import { downloadProtocolTemplate } from "./templateApi";

type TaggedStep = 1 | 2 | 3;

type StepDefinition = {
  id: TaggedStep;
  title: string;
  shortTitle: string;
  description: string;
};

const STEPS: StepDefinition[] = [
  {
    id: 1,
    title: "Preparar archivos",
    shortTitle: "Preparar",
    description: "Captura las etiquetas y crea la estructura de carpetas.",
  },
  {
    id: 2,
    title: "Validar etiquetas",
    shortTitle: "Validar",
    description: "Comprueba que el Word y el Excel coincidan.",
  },
  {
    id: 3,
    title: "Generar documento",
    shortTitle: "Generar",
    description: "Sube las fotografías y completa el Word.",
  },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function SelectedFile({
  file,
  label,
}: {
  file: File | null;
  label: string;
}) {
  if (!file) return null;

  return (
    <div className="mt-3 flex min-w-0 items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-sm font-black text-white">
        ✓
      </span>
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-700">
          {label}
        </p>
        <p className="truncate text-sm font-bold text-slate-900" title={file.name}>
          {file.name}
        </p>
        <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
      </div>
    </div>
  );
}

function TagList({
  title,
  tags,
}: {
  title: string;
  tags: string[];
}) {
  if (tags.length === 0) return null;

  return (
    <details className="group rounded-2xl border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 font-bold text-slate-800">
        <span>
          {title} ({tags.length})
        </span>
        <span className="transition group-open:rotate-180">⌄</span>
      </summary>
      <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto border-t border-slate-100 p-4">
        {tags.map((tag) => (
          <code
            key={tag}
            className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700"
          >
            {`{{${tag}}}`}
          </code>
        ))}
      </div>
    </details>
  );
}

function ValidationSummary({
  validation,
}: {
  validation: TaggedDocumentValidation;
}) {
  return (
    <section
      className={`rounded-3xl border p-5 ${
        validation.compatible
          ? "border-emerald-200 bg-emerald-50"
          : "border-amber-200 bg-amber-50"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-lg font-black text-white ${
            validation.compatible ? "bg-emerald-600" : "bg-amber-500"
          }`}
        >
          {validation.compatible ? "✓" : "!"}
        </div>
        <div>
          <h4 className="text-lg font-black text-slate-900">
            {validation.compatible
              ? "Word y Excel compatibles"
              : "Las etiquetas necesitan revisión"}
          </h4>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {validation.compatible
              ? "Todas las etiquetas coinciden. Ya puedes continuar con el ZIP de fotografías."
              : "Corrige las diferencias indicadas y vuelve a validar los archivos."}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {[
          ["Etiquetas en Word", validation.total_word_tags],
          ["Etiquetas en Excel", validation.total_excel_tags],
          ["Coincidencias", validation.total_matches],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-white bg-white/85 p-4 shadow-sm"
          >
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
              {label}
            </p>
            <p className="mt-2 text-3xl font-black text-slate-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-3">
        <TagList
          title="Etiquetas del Excel que faltan en Word"
          tags={validation.missing_in_word}
        />
        <TagList
          title="Etiquetas del Word que faltan en Excel"
          tags={validation.missing_in_excel}
        />

        {validation.duplicated_in_word.length > 0 && (
          <details className="group rounded-2xl border border-amber-200 bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 font-bold text-amber-800">
              <span>
                Etiquetas repetidas ({validation.duplicated_in_word.length})
              </span>
              <span className="transition group-open:rotate-180">⌄</span>
            </summary>
            <div className="space-y-2 border-t border-amber-100 p-4">
              {validation.duplicated_in_word.map((item) => (
                <p
                  key={item.tag}
                  className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900"
                >
                  {`{{${item.tag}}}`} aparece {item.occurrences} veces.
                </p>
              ))}
            </div>
          </details>
        )}

        {validation.generic_pending_texts.length > 0 && (
          <details className="group rounded-2xl border border-slate-200 bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 font-bold text-slate-700">
              <span>
                Textos “Pendiente” todavía sin etiqueta (
                {validation.generic_pending_texts.length})
              </span>
              <span className="transition group-open:rotate-180">⌄</span>
            </summary>
            <div className="max-h-52 space-y-2 overflow-y-auto border-t border-slate-100 p-4">
              {validation.generic_pending_texts.map((text, index) => (
                <p
                  key={`${text}-${index}`}
                  className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600"
                >
                  {text}
                </p>
              ))}
            </div>
          </details>
        )}
      </div>
    </section>
  );
}

function FlowStepper({
  currentStep,
  onStepChange,
  canOpenStep,
}: {
  currentStep: TaggedStep;
  onStepChange: (step: TaggedStep) => void;
  canOpenStep: (step: TaggedStep) => boolean;
}) {
  return (
    <ol className="grid gap-3 md:grid-cols-3">
      {STEPS.map((step, index) => {
        const active = currentStep === step.id;
        const completed = currentStep > step.id;
        const enabled = canOpenStep(step.id);

        return (
          <li key={step.id} className="relative">
            <button
              type="button"
              onClick={() => enabled && onStepChange(step.id)}
              disabled={!enabled}
              className={`flex h-full w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left transition ${
                active
                  ? "border-violet-500 bg-violet-50 shadow-sm"
                  : completed
                    ? "border-emerald-200 bg-emerald-50"
                    : enabled
                      ? "border-slate-200 bg-white hover:border-violet-300 hover:bg-violet-50/40"
                      : "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60"
              }`}
            >
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-black ${
                  active
                    ? "bg-violet-600 text-white"
                    : completed
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-200 text-slate-600"
                }`}
              >
                {completed ? "✓" : step.id}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-black text-slate-900">
                  {step.title}
                </span>
                <span className="mt-1 hidden text-xs leading-5 text-slate-500 lg:block">
                  {step.description}
                </span>
              </span>
            </button>

            {index < STEPS.length - 1 && (
              <span className="pointer-events-none absolute -right-2 top-1/2 z-10 hidden h-px w-4 bg-slate-300 md:block" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function TaggedDocumentSection() {
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [wordFile, setWordFile] = useState<File | null>(null);
  const [evidenceZip, setEvidenceZip] = useState<File | null>(null);
  const [validation, setValidation] =
    useState<TaggedDocumentValidation | null>(null);
  const [generationDiagnostics, setGenerationDiagnostics] =
    useState<DocumentDiagnosticsData | null>(null);
  const [currentStep, setCurrentStep] = useState<TaggedStep>(1);

  const [loadingFolders, setLoadingFolders] = useState(false);
  const [downloadingTagsTemplate, setDownloadingTagsTemplate] = useState(false);
  const [validating, setValidating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function resetFeedback() {
    setMessage("");
    setError("");
  }

  function handleExcelChange(file: File | null) {
    setExcelFile(file);
    setValidation(null);
    setCurrentStep(1);
    resetFeedback();
  }

  function handleWordChange(file: File | null) {
    setWordFile(file);
    setValidation(null);
    setCurrentStep(2);
    resetFeedback();
  }

  function handleEvidenceZipChange(file: File | null) {
    setEvidenceZip(file);
    resetFeedback();
  }

  function canOpenStep(step: TaggedStep): boolean {
    if (step === 1) return true;
    if (step === 2) return Boolean(excelFile);
    return Boolean(excelFile && wordFile && validation?.compatible);
  }

  async function handleDownloadTagsTemplate() {
    resetFeedback();

    try {
      setDownloadingTagsTemplate(true);
      await downloadProtocolTemplate("c5-tags-v1");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "No fue posible descargar el formato oficial.",
      );
    } finally {
      setDownloadingTagsTemplate(false);
    }
  }

  async function handleGenerateFolders() {
    resetFeedback();

    if (!excelFile) {
      setError("Selecciona el Excel de etiquetas.");
      return;
    }

    try {
      setLoadingFolders(true);
      await generateTaggedFolders(excelFile);
      setMessage(
        "Estructura descargada. Agrega las fotografías a las carpetas y continúa con la validación.",
      );
      setCurrentStep(2);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "No fue posible generar las carpetas.",
      );
    } finally {
      setLoadingFolders(false);
    }
  }

  async function handleValidate() {
    resetFeedback();

    if (!excelFile || !wordFile) {
      setError("Selecciona el Excel y el Word antes de validar.");
      return null;
    }

    try {
      setValidating(true);
      const result = await validateTaggedDocument(excelFile, wordFile);
      setValidation(result);

      if (result.compatible) {
        setMessage(
          "Validación correcta. Word y Excel coinciden; ya puedes agregar el ZIP de fotografías.",
        );
        setCurrentStep(3);
      }

      return result;
    } catch (caughtError) {
      setValidation(null);
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "No fue posible validar las etiquetas.",
      );
      return null;
    } finally {
      setValidating(false);
    }
  }

  async function handleGenerateDocument() {
    resetFeedback();

    if (!excelFile || !wordFile || !evidenceZip) {
      setError("Selecciona el Excel, el Word y el ZIP con fotografías.");
      return;
    }

    try {
      setGenerating(true);

      const currentValidation = validation?.compatible
        ? validation
        : await handleValidate();

      if (!currentValidation?.compatible) {
        setError("Corrige las etiquetas antes de generar el documento.");
        return;
      }

      const result = await generateValidatedTaggedDocument(
        excelFile,
        wordFile,
        evidenceZip,
      );
      setGenerationDiagnostics(result.diagnostics);
      setMessage("Documento completado y descargado correctamente.");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "No fue posible completar el documento.",
      );
    } finally {
      setGenerating(false);
    }
  }

  const canGenerate = Boolean(
    excelFile && wordFile && evidenceZip && validation?.compatible,
  );

  return (
    <section className="overflow-hidden rounded-4xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 bg-linear-to-br from-white via-violet-50/70 to-blue-50/70 p-6 md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-2xl text-white shadow-lg shadow-violet-200">
              ✦
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.25em] text-violet-600">
                Actualización inteligente
              </p>
              <h3 className="mt-2 text-2xl font-black text-slate-950 md:text-3xl">
                Completar Word existente
              </h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                Agrega únicamente las evidencias pendientes mediante etiquetas,
                sin volver a generar todo el protocolo.
              </p>
            </div>
          </div>

          <details className="group w-full rounded-2xl border border-violet-200 bg-white/80 lg:max-w-sm">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-violet-800">
              <span>Ver guía rápida de etiquetas</span>
              <span className="transition group-open:rotate-180">⌄</span>
            </summary>
            <div className="border-t border-violet-100 p-4 text-xs leading-5 text-slate-600">
              Escribe una etiqueta única en el punto exacto del Word y captura la
              misma clave en el Excel.
              <code className="mt-3 block overflow-x-auto rounded-xl bg-slate-950 px-3 py-2 font-mono font-bold text-violet-200">
                {"{{PENDIENTE_LIBERTAD_PISO_3}}"}
              </code>
            </div>
          </details>
        </div>

        <div className="mt-6">
          <FlowStepper
            currentStep={currentStep}
            onStepChange={setCurrentStep}
            canOpenStep={canOpenStep}
          />
        </div>
      </header>

      <div className="p-6 md:p-8">
        {(message || error) && (
          <div
            role="status"
            className={`mb-6 flex items-start gap-3 rounded-2xl border p-4 text-sm font-semibold ${
              error
                ? "border-red-200 bg-red-50 text-red-700"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/60 font-black">
              {error ? "!" : "✓"}
            </span>
            <span className="leading-6">{error || message}</span>
          </div>
        )}

        {currentStep === 1 && (
          <article className="mx-auto max-w-3xl">
            <div className="mb-6">
              <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
                Paso 1 de 3
              </p>
              <h4 className="mt-2 text-2xl font-black text-slate-950">
                Prepara el Excel y las carpetas
              </h4>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Descarga el formato oficial, captura las etiquetas pendientes y
                genera la estructura donde colocarás las fotografías.
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl border border-violet-200 bg-violet-50 p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-lg text-white">
                  ↓
                </span>
                <h5 className="mt-4 font-black text-violet-950">
                  Formato oficial de etiquetas
                </h5>
                <p className="mt-2 text-sm leading-6 text-violet-800">
                  Utiliza este archivo como base. No cambies los nombres de las
                  columnas.
                </p>
                <button
                  type="button"
                  onClick={handleDownloadTagsTemplate}
                  disabled={downloadingTagsTemplate}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-violet-600 px-4 py-3 text-sm font-black text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300"
                >
                  {downloadingTagsTemplate
                    ? "Descargando formato..."
                    : "Descargar formato Excel"}
                </button>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
                <FileInput
                  label="Excel de etiquetas"
                  name="tagged_excel_v2"
                  accept=".xlsx,.xls"
                  required
                  helperText="Debe contener las etiquetas y evidencias pendientes."
                  onChange={handleExcelChange}
                />
                <SelectedFile file={excelFile} label="Excel seleccionado" />
              </div>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                disabled={!excelFile}
                className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Continuar sin descargar ZIP
              </button>
              <button
                type="button"
                onClick={handleGenerateFolders}
                disabled={!excelFile || loadingFolders}
                className="rounded-2xl bg-violet-600 px-6 py-3 text-sm font-black text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:shadow-none"
              >
                {loadingFolders
                  ? "Generando estructura..."
                  : "Generar y descargar ZIP"}
              </button>
            </div>
          </article>
        )}

        {currentStep === 2 && (
          <article className="mx-auto max-w-4xl">
            <div className="mb-6">
              <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
                Paso 2 de 3
              </p>
              <h4 className="mt-2 text-2xl font-black text-slate-950">
                Valida el Word contra el Excel
              </h4>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                El sistema comprobará que cada etiqueta identifique un único
                punto y que no falte ninguna clave.
              </p>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
                <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">
                  Archivo conservado del paso anterior
                </p>
                <SelectedFile file={excelFile} label="Excel de etiquetas" />
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="mt-4 text-sm font-black text-violet-700 hover:text-violet-900"
                >
                  Cambiar Excel
                </button>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
                <FileInput
                  label="Word incompleto con etiquetas"
                  name="tagged_word_v2"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  required
                  helperText="Documento que contiene etiquetas entre llaves dobles."
                  onChange={handleWordChange}
                />
                <SelectedFile file={wordFile} label="Word seleccionado" />
              </div>
            </div>

            {validation && (
              <div className="mt-6">
                <ValidationSummary validation={validation} />
              </div>
            )}

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50"
              >
                ← Volver
              </button>
              <button
                type="button"
                onClick={handleValidate}
                disabled={!excelFile || !wordFile || validating}
                className="rounded-2xl bg-violet-600 px-6 py-3 text-sm font-black text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:shadow-none"
              >
                {validating ? "Validando etiquetas..." : "Validar archivos"}
              </button>
            </div>
          </article>
        )}

        {currentStep === 3 && (
          <article className="mx-auto max-w-4xl">
            <div className="mb-6">
              <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
                Paso 3 de 3
              </p>
              <h4 className="mt-2 text-2xl font-black text-slate-950">
                Genera el documento completo
              </h4>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Selecciona el ZIP que contiene las fotografías organizadas por
                etiqueta. El Word y el Excel ya fueron validados.
              </p>
            </div>

            <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
              <div className="space-y-3 rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 font-black text-white">
                    ✓
                  </span>
                  <div>
                    <p className="font-black text-emerald-950">
                      Archivos validados
                    </p>
                    <p className="text-xs text-emerald-700">
                      Las etiquetas coinciden correctamente.
                    </p>
                  </div>
                </div>
                <SelectedFile file={excelFile} label="Excel" />
                <SelectedFile file={wordFile} label="Word" />
              </div>

              <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
                <FileInput
                  label="ZIP con fotografías por etiqueta"
                  name="tagged_evidence_zip_v2"
                  accept=".zip,application/zip,application/x-zip-compressed"
                  required
                  helperText="ZIP generado por el sistema y completado con fotografías."
                  onChange={handleEvidenceZipChange}
                />
                <SelectedFile file={evidenceZip} label="ZIP seleccionado" />
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs leading-5 text-blue-800">
              El documento original no se reemplazará. El navegador descargará
              una nueva versión completa.
            </div>

            {generationDiagnostics && (
              <div className="mt-6">
                <DocumentDiagnostics
                  diagnostics={generationDiagnostics}
                  title="Documento actualizado"
                />
              </div>
            )}

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50"
              >
                ← Volver a validar
              </button>
              <button
                type="button"
                onClick={handleGenerateDocument}
                disabled={!canGenerate || generating}
                className="rounded-2xl bg-slate-950 px-7 py-3 text-sm font-black text-white shadow-xl transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {generating
                  ? "Completando documento..."
                  : "Generar y descargar documento"}
              </button>
            </div>
          </article>
        )}
      </div>
    </section>
  );
}





// "use client";

// import { useState } from "react";
// import { FileInput } from "@/components/FileInput";
// import { DocumentDiagnostics } from "@/components/DocumentDiagnostics";
// import type { DocumentDiagnosticsData } from "@/components/DocumentDiagnostics";
// import {
//   generateTaggedFolders,
//   generateValidatedTaggedDocument,
//   TaggedDocumentValidation,
//   validateTaggedDocument,
// } from "./taggedDocumentApi";

// type TaggedStep = 1 | 2 | 3;

// type StepDefinition = {
//   id: TaggedStep;
//   title: string;
//   shortTitle: string;
//   description: string;
// };

// const STEPS: StepDefinition[] = [
//   {
//     id: 1,
//     title: "Preparar archivos",
//     shortTitle: "Preparar",
//     description: "Captura las etiquetas y crea la estructura de carpetas.",
//   },
//   {
//     id: 2,
//     title: "Validar etiquetas",
//     shortTitle: "Validar",
//     description: "Comprueba que el Word y el Excel coincidan.",
//   },
//   {
//     id: 3,
//     title: "Generar documento",
//     shortTitle: "Generar",
//     description: "Sube las fotografías y completa el Word.",
//   },
// ];

// function formatFileSize(bytes: number): string {
//   if (bytes < 1024) return `${bytes} B`;
//   if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
//   return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
// }

// function SelectedFile({
//   file,
//   label,
// }: {
//   file: File | null;
//   label: string;
// }) {
//   if (!file) return null;

//   return (
//     <div className="mt-3 flex min-w-0 items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
//       <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-sm font-black text-white">
//         ✓
//       </span>
//       <div className="min-w-0">
//         <p className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-700">
//           {label}
//         </p>
//         <p className="truncate text-sm font-bold text-slate-900" title={file.name}>
//           {file.name}
//         </p>
//         <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
//       </div>
//     </div>
//   );
// }

// function TagList({
//   title,
//   tags,
// }: {
//   title: string;
//   tags: string[];
// }) {
//   if (tags.length === 0) return null;

//   return (
//     <details className="group rounded-2xl border border-slate-200 bg-white">
//       <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 font-bold text-slate-800">
//         <span>
//           {title} ({tags.length})
//         </span>
//         <span className="transition group-open:rotate-180">⌄</span>
//       </summary>
//       <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto border-t border-slate-100 p-4">
//         {tags.map((tag) => (
//           <code
//             key={tag}
//             className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700"
//           >
//             {`{{${tag}}}`}
//           </code>
//         ))}
//       </div>
//     </details>
//   );
// }

// function ValidationSummary({
//   validation,
// }: {
//   validation: TaggedDocumentValidation;
// }) {
//   return (
//     <section
//       className={`rounded-3xl border p-5 ${
//         validation.compatible
//           ? "border-emerald-200 bg-emerald-50"
//           : "border-amber-200 bg-amber-50"
//       }`}
//     >
//       <div className="flex items-start gap-3">
//         <div
//           className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-lg font-black text-white ${
//             validation.compatible ? "bg-emerald-600" : "bg-amber-500"
//           }`}
//         >
//           {validation.compatible ? "✓" : "!"}
//         </div>
//         <div>
//           <h4 className="text-lg font-black text-slate-900">
//             {validation.compatible
//               ? "Word y Excel compatibles"
//               : "Las etiquetas necesitan revisión"}
//           </h4>
//           <p className="mt-1 text-sm leading-6 text-slate-600">
//             {validation.compatible
//               ? "Todas las etiquetas coinciden. Ya puedes continuar con el ZIP de fotografías."
//               : "Corrige las diferencias indicadas y vuelve a validar los archivos."}
//           </p>
//         </div>
//       </div>

//       <div className="mt-5 grid gap-3 sm:grid-cols-3">
//         {[
//           ["Etiquetas en Word", validation.total_word_tags],
//           ["Etiquetas en Excel", validation.total_excel_tags],
//           ["Coincidencias", validation.total_matches],
//         ].map(([label, value]) => (
//           <div
//             key={label}
//             className="rounded-2xl border border-white bg-white/85 p-4 shadow-sm"
//           >
//             <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
//               {label}
//             </p>
//             <p className="mt-2 text-3xl font-black text-slate-900">{value}</p>
//           </div>
//         ))}
//       </div>

//       <div className="mt-4 space-y-3">
//         <TagList
//           title="Etiquetas del Excel que faltan en Word"
//           tags={validation.missing_in_word}
//         />
//         <TagList
//           title="Etiquetas del Word que faltan en Excel"
//           tags={validation.missing_in_excel}
//         />

//         {validation.duplicated_in_word.length > 0 && (
//           <details className="group rounded-2xl border border-amber-200 bg-white">
//             <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 font-bold text-amber-800">
//               <span>
//                 Etiquetas repetidas ({validation.duplicated_in_word.length})
//               </span>
//               <span className="transition group-open:rotate-180">⌄</span>
//             </summary>
//             <div className="space-y-2 border-t border-amber-100 p-4">
//               {validation.duplicated_in_word.map((item) => (
//                 <p
//                   key={item.tag}
//                   className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900"
//                 >
//                   {`{{${item.tag}}}`} aparece {item.occurrences} veces.
//                 </p>
//               ))}
//             </div>
//           </details>
//         )}

//         {validation.generic_pending_texts.length > 0 && (
//           <details className="group rounded-2xl border border-slate-200 bg-white">
//             <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 font-bold text-slate-700">
//               <span>
//                 Textos “Pendiente” todavía sin etiqueta (
//                 {validation.generic_pending_texts.length})
//               </span>
//               <span className="transition group-open:rotate-180">⌄</span>
//             </summary>
//             <div className="max-h-52 space-y-2 overflow-y-auto border-t border-slate-100 p-4">
//               {validation.generic_pending_texts.map((text, index) => (
//                 <p
//                   key={`${text}-${index}`}
//                   className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600"
//                 >
//                   {text}
//                 </p>
//               ))}
//             </div>
//           </details>
//         )}
//       </div>
//     </section>
//   );
// }

// function FlowStepper({
//   currentStep,
//   onStepChange,
//   canOpenStep,
// }: {
//   currentStep: TaggedStep;
//   onStepChange: (step: TaggedStep) => void;
//   canOpenStep: (step: TaggedStep) => boolean;
// }) {
//   return (
//     <ol className="grid gap-3 md:grid-cols-3">
//       {STEPS.map((step, index) => {
//         const active = currentStep === step.id;
//         const completed = currentStep > step.id;
//         const enabled = canOpenStep(step.id);

//         return (
//           <li key={step.id} className="relative">
//             <button
//               type="button"
//               onClick={() => enabled && onStepChange(step.id)}
//               disabled={!enabled}
//               className={`flex h-full w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left transition ${
//                 active
//                   ? "border-violet-500 bg-violet-50 shadow-sm"
//                   : completed
//                     ? "border-emerald-200 bg-emerald-50"
//                     : enabled
//                       ? "border-slate-200 bg-white hover:border-violet-300 hover:bg-violet-50/40"
//                       : "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60"
//               }`}
//             >
//               <span
//                 className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-black ${
//                   active
//                     ? "bg-violet-600 text-white"
//                     : completed
//                       ? "bg-emerald-600 text-white"
//                       : "bg-slate-200 text-slate-600"
//                 }`}
//               >
//                 {completed ? "✓" : step.id}
//               </span>
//               <span className="min-w-0">
//                 <span className="block text-sm font-black text-slate-900">
//                   {step.title}
//                 </span>
//                 <span className="mt-1 hidden text-xs leading-5 text-slate-500 lg:block">
//                   {step.description}
//                 </span>
//               </span>
//             </button>

//             {index < STEPS.length - 1 && (
//               <span className="pointer-events-none absolute -right-2 top-1/2 z-10 hidden h-px w-4 bg-slate-300 md:block" />
//             )}
//           </li>
//         );
//       })}
//     </ol>
//   );
// }

// export function TaggedDocumentSection() {
//   const [excelFile, setExcelFile] = useState<File | null>(null);
//   const [wordFile, setWordFile] = useState<File | null>(null);
//   const [evidenceZip, setEvidenceZip] = useState<File | null>(null);
//   const [validation, setValidation] =
//     useState<TaggedDocumentValidation | null>(null);
//   const [generationDiagnostics, setGenerationDiagnostics] =
//     useState<DocumentDiagnosticsData | null>(null);
//   const [currentStep, setCurrentStep] = useState<TaggedStep>(1);

//   const [loadingFolders, setLoadingFolders] = useState(false);
//   const [validating, setValidating] = useState(false);
//   const [generating, setGenerating] = useState(false);
//   const [message, setMessage] = useState("");
//   const [error, setError] = useState("");

//   function resetFeedback() {
//     setMessage("");
//     setError("");
//   }

//   function handleExcelChange(file: File | null) {
//     setExcelFile(file);
//     setValidation(null);
//     setCurrentStep(1);
//     resetFeedback();
//   }

//   function handleWordChange(file: File | null) {
//     setWordFile(file);
//     setValidation(null);
//     setCurrentStep(2);
//     resetFeedback();
//   }

//   function handleEvidenceZipChange(file: File | null) {
//     setEvidenceZip(file);
//     resetFeedback();
//   }

//   function canOpenStep(step: TaggedStep): boolean {
//     if (step === 1) return true;
//     if (step === 2) return Boolean(excelFile);
//     return Boolean(excelFile && wordFile && validation?.compatible);
//   }

//   async function handleGenerateFolders() {
//     resetFeedback();

//     if (!excelFile) {
//       setError("Selecciona el Excel de etiquetas.");
//       return;
//     }

//     try {
//       setLoadingFolders(true);
//       await generateTaggedFolders(excelFile);
//       setMessage(
//         "Estructura descargada. Agrega las fotografías a las carpetas y continúa con la validación.",
//       );
//       setCurrentStep(2);
//     } catch (caughtError) {
//       setError(
//         caughtError instanceof Error
//           ? caughtError.message
//           : "No fue posible generar las carpetas.",
//       );
//     } finally {
//       setLoadingFolders(false);
//     }
//   }

//   async function handleValidate() {
//     resetFeedback();

//     if (!excelFile || !wordFile) {
//       setError("Selecciona el Excel y el Word antes de validar.");
//       return null;
//     }

//     try {
//       setValidating(true);
//       const result = await validateTaggedDocument(excelFile, wordFile);
//       setValidation(result);

//       if (result.compatible) {
//         setMessage(
//           "Validación correcta. Word y Excel coinciden; ya puedes agregar el ZIP de fotografías.",
//         );
//         setCurrentStep(3);
//       }

//       return result;
//     } catch (caughtError) {
//       setValidation(null);
//       setError(
//         caughtError instanceof Error
//           ? caughtError.message
//           : "No fue posible validar las etiquetas.",
//       );
//       return null;
//     } finally {
//       setValidating(false);
//     }
//   }

//   async function handleGenerateDocument() {
//     resetFeedback();

//     if (!excelFile || !wordFile || !evidenceZip) {
//       setError("Selecciona el Excel, el Word y el ZIP con fotografías.");
//       return;
//     }

//     try {
//       setGenerating(true);

//       const currentValidation = validation?.compatible
//         ? validation
//         : await handleValidate();

//       if (!currentValidation?.compatible) {
//         setError("Corrige las etiquetas antes de generar el documento.");
//         return;
//       }

//       const result = await generateValidatedTaggedDocument(
//         excelFile,
//         wordFile,
//         evidenceZip,
//       );
//       setGenerationDiagnostics(result.diagnostics);
//       setMessage("Documento completado y descargado correctamente.");
//     } catch (caughtError) {
//       setError(
//         caughtError instanceof Error
//           ? caughtError.message
//           : "No fue posible completar el documento.",
//       );
//     } finally {
//       setGenerating(false);
//     }
//   }

//   const canGenerate = Boolean(
//     excelFile && wordFile && evidenceZip && validation?.compatible,
//   );

//   return (
//     <section className="overflow-hidden rounded-4xl border border-slate-200 bg-white shadow-sm">
//       <header className="border-b border-slate-200 bg-linear-to-br from-white via-violet-50/70 to-blue-50/70 p-6 md:p-8">
//         <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
//           <div className="flex items-start gap-4">
//             <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-2xl text-white shadow-lg shadow-violet-200">
//               ✦
//             </div>
//             <div>
//               <p className="text-xs font-black uppercase tracking-[0.25em] text-violet-600">
//                 Actualización inteligente
//               </p>
//               <h3 className="mt-2 text-2xl font-black text-slate-950 md:text-3xl">
//                 Completar Word existente
//               </h3>
//               <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
//                 Agrega únicamente las evidencias pendientes mediante etiquetas,
//                 sin volver a generar todo el protocolo.
//               </p>
//             </div>
//           </div>

//           <details className="group w-full rounded-2xl border border-violet-200 bg-white/80 lg:max-w-sm">
//             <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-violet-800">
//               <span>Ver guía rápida de etiquetas</span>
//               <span className="transition group-open:rotate-180">⌄</span>
//             </summary>
//             <div className="border-t border-violet-100 p-4 text-xs leading-5 text-slate-600">
//               Escribe una etiqueta única en el punto exacto del Word y captura la
//               misma clave en el Excel.
//               <code className="mt-3 block overflow-x-auto rounded-xl bg-slate-950 px-3 py-2 font-mono font-bold text-violet-200">
//                 {"{{PENDIENTE_LIBERTAD_PISO_3}}"}
//               </code>
//             </div>
//           </details>
//         </div>

//         <div className="mt-6">
//           <FlowStepper
//             currentStep={currentStep}
//             onStepChange={setCurrentStep}
//             canOpenStep={canOpenStep}
//           />
//         </div>
//       </header>

//       <div className="p-6 md:p-8">
//         {(message || error) && (
//           <div
//             role="status"
//             className={`mb-6 flex items-start gap-3 rounded-2xl border p-4 text-sm font-semibold ${
//               error
//                 ? "border-red-200 bg-red-50 text-red-700"
//                 : "border-emerald-200 bg-emerald-50 text-emerald-700"
//             }`}
//           >
//             <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/60 font-black">
//               {error ? "!" : "✓"}
//             </span>
//             <span className="leading-6">{error || message}</span>
//           </div>
//         )}

//         {currentStep === 1 && (
//           <article className="mx-auto max-w-3xl">
//             <div className="mb-6">
//               <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
//                 Paso 1 de 3
//               </p>
//               <h4 className="mt-2 text-2xl font-black text-slate-950">
//                 Prepara el Excel y las carpetas
//               </h4>
//               <p className="mt-2 text-sm leading-6 text-slate-500">
//                 Descarga el formato oficial, captura las etiquetas pendientes y
//                 genera la estructura donde colocarás las fotografías.
//               </p>
//             </div>

//             <div className="grid gap-5 md:grid-cols-[0.9fr_1.1fr]">
//               <div className="rounded-3xl border border-violet-200 bg-violet-50 p-5">
//                 <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-lg text-white">
//                   ↓
//                 </span>
//                 <h5 className="mt-4 font-black text-violet-950">
//                   Formato oficial de etiquetas
//                 </h5>
//                 <p className="mt-2 text-sm leading-6 text-violet-800">
//                   Utiliza este archivo como base. No cambies los nombres de las
//                   columnas.
//                 </p>
//                 <a
//                   href="/templates/C5_Etiquetas_Word_v1.xlsx"
//                   download
//                   className="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-violet-600 px-4 py-3 text-sm font-black text-white transition hover:bg-violet-700"
//                 >
//                   Descargar formato Excel
//                 </a>
//               </div>

//               <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
//                 <FileInput
//                   label="Excel de etiquetas"
//                   name="tagged_excel_v2"
//                   accept=".xlsx,.xls"
//                   required
//                   helperText="Debe contener las etiquetas y evidencias pendientes."
//                   onChange={handleExcelChange}
//                 />
//                 <SelectedFile file={excelFile} label="Excel seleccionado" />
//               </div>
//             </div>

//             <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
//               <button
//                 type="button"
//                 onClick={() => setCurrentStep(2)}
//                 disabled={!excelFile}
//                 className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
//               >
//                 Continuar sin descargar ZIP
//               </button>
//               <button
//                 type="button"
//                 onClick={handleGenerateFolders}
//                 disabled={!excelFile || loadingFolders}
//                 className="rounded-2xl bg-violet-600 px-6 py-3 text-sm font-black text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:shadow-none"
//               >
//                 {loadingFolders
//                   ? "Generando estructura..."
//                   : "Generar y descargar ZIP"}
//               </button>
//             </div>
//           </article>
//         )}

//         {currentStep === 2 && (
//           <article className="mx-auto max-w-4xl">
//             <div className="mb-6">
//               <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
//                 Paso 2 de 3
//               </p>
//               <h4 className="mt-2 text-2xl font-black text-slate-950">
//                 Valida el Word contra el Excel
//               </h4>
//               <p className="mt-2 text-sm leading-6 text-slate-500">
//                 El sistema comprobará que cada etiqueta identifique un único
//                 punto y que no falte ninguna clave.
//               </p>
//             </div>

//             <div className="grid gap-5 lg:grid-cols-2">
//               <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
//                 <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">
//                   Archivo conservado del paso anterior
//                 </p>
//                 <SelectedFile file={excelFile} label="Excel de etiquetas" />
//                 <button
//                   type="button"
//                   onClick={() => setCurrentStep(1)}
//                   className="mt-4 text-sm font-black text-violet-700 hover:text-violet-900"
//                 >
//                   Cambiar Excel
//                 </button>
//               </div>

//               <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
//                 <FileInput
//                   label="Word incompleto con etiquetas"
//                   name="tagged_word_v2"
//                   accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
//                   required
//                   helperText="Documento que contiene etiquetas entre llaves dobles."
//                   onChange={handleWordChange}
//                 />
//                 <SelectedFile file={wordFile} label="Word seleccionado" />
//               </div>
//             </div>

//             {validation && (
//               <div className="mt-6">
//                 <ValidationSummary validation={validation} />
//               </div>
//             )}

//             <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
//               <button
//                 type="button"
//                 onClick={() => setCurrentStep(1)}
//                 className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50"
//               >
//                 ← Volver
//               </button>
//               <button
//                 type="button"
//                 onClick={handleValidate}
//                 disabled={!excelFile || !wordFile || validating}
//                 className="rounded-2xl bg-violet-600 px-6 py-3 text-sm font-black text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:shadow-none"
//               >
//                 {validating ? "Validando etiquetas..." : "Validar archivos"}
//               </button>
//             </div>
//           </article>
//         )}

//         {currentStep === 3 && (
//           <article className="mx-auto max-w-4xl">
//             <div className="mb-6">
//               <p className="text-xs font-black uppercase tracking-[0.2em] text-violet-600">
//                 Paso 3 de 3
//               </p>
//               <h4 className="mt-2 text-2xl font-black text-slate-950">
//                 Genera el documento completo
//               </h4>
//               <p className="mt-2 text-sm leading-6 text-slate-500">
//                 Selecciona el ZIP que contiene las fotografías organizadas por
//                 etiqueta. El Word y el Excel ya fueron validados.
//               </p>
//             </div>

//             <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
//               <div className="space-y-3 rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
//                 <div className="flex items-center gap-3">
//                   <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 font-black text-white">
//                     ✓
//                   </span>
//                   <div>
//                     <p className="font-black text-emerald-950">
//                       Archivos validados
//                     </p>
//                     <p className="text-xs text-emerald-700">
//                       Las etiquetas coinciden correctamente.
//                     </p>
//                   </div>
//                 </div>
//                 <SelectedFile file={excelFile} label="Excel" />
//                 <SelectedFile file={wordFile} label="Word" />
//               </div>

//               <div className="rounded-3xl border border-slate-200 bg-slate-50/70 p-5">
//                 <FileInput
//                   label="ZIP con fotografías por etiqueta"
//                   name="tagged_evidence_zip_v2"
//                   accept=".zip,application/zip,application/x-zip-compressed"
//                   required
//                   helperText="ZIP generado por el sistema y completado con fotografías."
//                   onChange={handleEvidenceZipChange}
//                 />
//                 <SelectedFile file={evidenceZip} label="ZIP seleccionado" />
//               </div>
//             </div>

//             <div className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs leading-5 text-blue-800">
//               El documento original no se reemplazará. El navegador descargará
//               una nueva versión completa.
//             </div>

//             {generationDiagnostics && (
//               <div className="mt-6">
//                 <DocumentDiagnostics
//                   diagnostics={generationDiagnostics}
//                   title="Documento actualizado"
//                 />
//               </div>
//             )}

//             <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
//               <button
//                 type="button"
//                 onClick={() => setCurrentStep(2)}
//                 className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:bg-slate-50"
//               >
//                 ← Volver a validar
//               </button>
//               <button
//                 type="button"
//                 onClick={handleGenerateDocument}
//                 disabled={!canGenerate || generating}
//                 className="rounded-2xl bg-slate-950 px-7 py-3 text-sm font-black text-white shadow-xl transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
//               >
//                 {generating
//                   ? "Completando documento..."
//                   : "Generar y descargar documento"}
//               </button>
//             </div>
//           </article>
//         )}
//       </div>
//     </section>
//   );
// }




