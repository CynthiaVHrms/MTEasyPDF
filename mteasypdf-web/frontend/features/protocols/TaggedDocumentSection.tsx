"use client";

import {
  useMemo,
  useState,
} from "react";

import { FileInput } from "@/components/FileInput";

import {
  generateTaggedFolders,
  generateValidatedTaggedDocument,
  TaggedDocumentValidation,
  validateTaggedDocument,
} from "./taggedDocumentApi";


function TagBadge({
  tag,
  tone = "slate",
}: {
  tag: string;
  tone?: "slate" | "red" | "amber" | "emerald";
}) {
  const toneClasses = {
    slate: "border-slate-200 bg-slate-50 text-slate-700",
    red: "border-red-200 bg-red-50 text-red-700",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    emerald:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  };

  return (
    <span
      className={[
        "inline-flex max-w-full rounded-lg border px-2.5 py-1",
        "font-mono text-xs font-semibold break-all",
        toneClasses[tone],
      ].join(" ")}
    >
      {`{{${tag}}}`}
    </span>
  );
}


function ValidationCounter({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "blue" | "emerald" | "amber" | "red";
}) {
  const toneClasses = {
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    emerald:
      "border-emerald-200 bg-emerald-50 text-emerald-800",
    amber:
      "border-amber-200 bg-amber-50 text-amber-900",
    red: "border-red-200 bg-red-50 text-red-800",
  };

  return (
    <div
      className={[
        "rounded-2xl border p-4",
        toneClasses[tone],
      ].join(" ")}
    >
      <p className="text-xs font-bold uppercase tracking-[0.15em]">
        {label}
      </p>

      <p className="mt-2 text-3xl font-black">
        {value}
      </p>
    </div>
  );
}


function ValidationPanel({
  validation,
}: {
  validation: TaggedDocumentValidation;
}) {
  const hasProblems = !validation.compatible;

  return (
    <section
      className={[
        "mt-6 rounded-3xl border p-5",
        hasProblems
          ? "border-amber-200 bg-amber-50/70"
          : "border-emerald-200 bg-emerald-50/70",
      ].join(" ")}
    >
      <div className="flex items-start gap-4">
        <div
          className={[
            "flex h-11 w-11 shrink-0 items-center justify-center",
            "rounded-2xl text-lg font-black text-white",
            hasProblems
              ? "bg-amber-500"
              : "bg-emerald-600",
          ].join(" ")}
        >
          {hasProblems ? "!" : "✓"}
        </div>

        <div>
          <h4 className="text-lg font-black text-slate-900">
            {hasProblems
              ? "Las etiquetas necesitan revisión"
              : "Word y Excel compatibles"}
          </h4>

          <p className="mt-1 text-sm leading-6 text-slate-600">
            {hasProblems
              ? "Corrige las diferencias mostradas antes de generar el documento completo."
              : "Todas las etiquetas del Word coinciden con las etiquetas capturadas en el Excel."}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <ValidationCounter
          label="Etiquetas en Word"
          value={validation.total_word_tags}
          tone="blue"
        />

        <ValidationCounter
          label="Etiquetas en Excel"
          value={validation.total_excel_tags}
          tone="blue"
        />

        <ValidationCounter
          label="Coincidencias"
          value={validation.total_matches}
          tone="emerald"
        />
      </div>

      {validation.missing_in_word.length > 0 && (
        <details className="mt-4 rounded-2xl border border-red-200 bg-white p-4">
          <summary className="cursor-pointer font-bold text-red-700">
            Etiquetas del Excel que faltan en Word (
            {validation.missing_in_word.length})
          </summary>

          <div className="mt-3 flex flex-wrap gap-2">
            {validation.missing_in_word.map((tag) => (
              <TagBadge
                key={tag}
                tag={tag}
                tone="red"
              />
            ))}
          </div>
        </details>
      )}

      {validation.missing_in_excel.length > 0 && (
        <details className="mt-4 rounded-2xl border border-red-200 bg-white p-4">
          <summary className="cursor-pointer font-bold text-red-700">
            Etiquetas del Word que faltan en Excel (
            {validation.missing_in_excel.length})
          </summary>

          <div className="mt-3 flex flex-wrap gap-2">
            {validation.missing_in_excel.map((tag) => (
              <TagBadge
                key={tag}
                tag={tag}
                tone="red"
              />
            ))}
          </div>
        </details>
      )}

      {validation.duplicated_in_word.length > 0 && (
        <details className="mt-4 rounded-2xl border border-amber-200 bg-white p-4">
          <summary className="cursor-pointer font-bold text-amber-800">
            Etiquetas repetidas dentro del Word (
            {validation.duplicated_in_word.length})
          </summary>

          <div className="mt-3 space-y-2">
            {validation.duplicated_in_word.map((item) => (
              <div
                key={item.tag}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50 p-3"
              >
                <TagBadge
                  tag={item.tag}
                  tone="amber"
                />

                <span className="text-xs font-bold text-amber-800">
                  {item.occurrences} apariciones
                </span>
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs leading-5 text-amber-800">
            Cada etiqueta debe aparecer una sola vez para identificar
            exactamente un punto de inserción.
          </p>
        </details>
      )}

      {validation.generic_pending_texts.length > 0 && (
        <details className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer font-bold text-slate-700">
            Textos “Pendiente” todavía sin etiqueta (
            {validation.generic_pending_texts.length})
          </summary>

          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1">
            {validation.generic_pending_texts.map(
              (text, index) => (
                <p
                  key={`${text}-${index}`}
                  className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600"
                >
                  {text}
                </p>
              ),
            )}
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-500">
            Estos textos no se reemplazan automáticamente. Agrega una
            etiqueta única debajo del texto cuando esa sección deba
            completarse.
          </p>
        </details>
      )}
    </section>
  );
}


export function TaggedDocumentSection() {
  const [excelFile, setExcelFile] = useState<File | null>(
    null,
  );
  const [wordFile, setWordFile] = useState<File | null>(
    null,
  );
  const [evidenceZip, setEvidenceZip] = useState<File | null>(
    null,
  );

  const [validation, setValidation] =
    useState<TaggedDocumentValidation | null>(null);

  const [validating, setValidating] = useState(false);
  const [generatingFolders, setGeneratingFolders] =
    useState(false);
  const [generatingDocument, setGeneratingDocument] =
    useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const canValidate = Boolean(
    excelFile && wordFile,
  );

  const canGenerate = Boolean(
    excelFile &&
      wordFile &&
      evidenceZip &&
      validation?.compatible,
  );

  const selectedFilesChanged = useMemo(
    () => ({
      excel: excelFile?.name ?? "",
      word: wordFile?.name ?? "",
    }),
    [excelFile, wordFile],
  );

  function clearFeedback() {
    setMessage("");
    setError("");
  }

  function handleExcelChange(file: File | null) {
    setExcelFile(file);
    setValidation(null);
    clearFeedback();
  }

  function handleWordChange(file: File | null) {
    setWordFile(file);
    setValidation(null);
    clearFeedback();
  }

  async function handleGenerateFolders() {
    clearFeedback();

    if (!excelFile) {
      setError(
        "Selecciona el Excel de etiquetas para generar las carpetas.",
      );
      return;
    }

    try {
      setGeneratingFolders(true);

      await generateTaggedFolders(
        excelFile,
      );

      setMessage(
        "Estructura de carpetas descargada correctamente.",
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Ocurrió un error generando las carpetas.",
      );
    } finally {
      setGeneratingFolders(false);
    }
  }

  async function handleValidate() {
    clearFeedback();

    if (!excelFile || !wordFile) {
      setError(
        "Selecciona el Excel y el Word antes de validar.",
      );
      return null;
    }

    try {
      setValidating(true);

      const result = await validateTaggedDocument(
        excelFile,
        wordFile,
      );

      setValidation(result);

      if (result.compatible) {
        setMessage(
          "Las etiquetas del Word y del Excel coinciden correctamente.",
        );
      }

      return result;
    } catch (caughtError) {
      setValidation(null);

      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Ocurrió un error validando las etiquetas.",
      );

      return null;
    } finally {
      setValidating(false);
    }
  }

  async function handleGenerateDocument() {
    clearFeedback();

    if (!excelFile || !wordFile || !evidenceZip) {
      setError(
        "Selecciona el Excel, el Word incompleto y el ZIP con fotografías.",
      );
      return;
    }

    try {
      setGeneratingDocument(true);

      const currentValidation =
        validation?.compatible
          ? validation
          : await handleValidate();

      if (!currentValidation?.compatible) {
        setError(
          "Corrige las diferencias de etiquetas antes de generar el documento.",
        );
        return;
      }

      await generateValidatedTaggedDocument(
        excelFile,
        wordFile,
        evidenceZip,
      );

      setMessage(
        "Documento completado y descargado correctamente.",
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Ocurrió un error completando el documento.",
      );
    } finally {
      setGeneratingDocument(false);
    }
  }

  return (
    <section className="rounded-4xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
      <div className="flex items-start gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-2xl text-white shadow-lg shadow-violet-200">
          ✦
        </div>

        <div>
          <p className="text-xs font-black uppercase tracking-[0.25em] text-violet-600">
            Actualización inteligente
          </p>

          <h3 className="mt-2 text-2xl font-black text-slate-900">
            3. Completar Word mediante etiquetas
          </h3>

          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">
            Completa únicamente las secciones pendientes de un Word ya
            elaborado, sin volver a generar todo el protocolo.
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-3xl border border-violet-200 bg-linear-to-br from-violet-50 to-blue-50 p-5">
        <p className="text-sm font-black text-violet-950">
          Cómo preparar el documento
        </p>

        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {[
            [
              "1",
              "Abrir Word",
              "Localiza cada sección pendiente.",
            ],
            [
              "2",
              "Agregar etiqueta",
              "Escribe una etiqueta única en el punto exacto.",
            ],
            [
              "3",
              "Capturar Excel",
              "Utiliza la misma etiqueta dentro del formato.",
            ],
            [
              "4",
              "Validar",
              "El sistema comprobará que Word y Excel coincidan.",
            ],
          ].map(([number, title, description]) => (
            <div
              key={number}
              className="rounded-2xl border border-white bg-white/80 p-4"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-600 text-sm font-black text-white">
                {number}
              </span>

              <p className="mt-3 text-sm font-black text-slate-900">
                {title}
              </p>

              <p className="mt-1 text-xs leading-5 text-slate-500">
                {description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-2xl border border-violet-200 bg-white p-4">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-violet-600">
            Ejemplo recomendado
          </p>

          <code className="mt-2 block overflow-x-auto rounded-xl bg-slate-950 px-4 py-3 font-mono text-sm font-bold text-violet-200">
            {"{{PENDIENTE_LIBERTAD_PISO_3}}"}
          </code>

          <p className="mt-3 text-xs leading-5 text-slate-500">
            No utilices solamente “Pendiente por visitar”. El sistema
            nunca reemplazará textos genéricos automáticamente.
          </p>
        </div>
      </div>

      {(message || error) && (
        <div
          className={[
            "mt-6 rounded-2xl border p-4 text-sm font-semibold",
            error
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700",
          ].join(" ")}
        >
          {error || message}
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <article className="rounded-3xl border border-slate-200 bg-slate-50/60 p-5">
          <h4 className="text-lg font-black text-slate-900">
            A. Preparar estructura de fotografías
          </h4>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Descarga el formato, captura las etiquetas y genera las
            carpetas donde colocarás las fotografías.
          </p>

          <a
            href="/templates/C5_Etiquetas_Word_v1.xlsx"
            download
            className="mt-5 inline-flex rounded-xl bg-violet-600 px-4 py-3 text-sm font-black text-white transition hover:bg-violet-700"
          >
            Descargar formato Excel
          </a>

          <div className="mt-5">
            <FileInput
              label="Excel de etiquetas"
              name="tagged_excel_v2"
              accept=".xlsx,.xls"
              required
              helperText="Debe contener Etiqueta, Seccion, Evidencia y los campos opcionales."
              onChange={handleExcelChange}
            />
          </div>

          <button
            type="button"
            onClick={handleGenerateFolders}
            disabled={!excelFile || generatingFolders}
            className="mt-5 w-full rounded-2xl bg-violet-600 px-5 py-4 text-sm font-black text-white shadow-lg transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {generatingFolders
              ? "Generando estructura..."
              : "Descargar ZIP de carpetas"}
          </button>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-slate-50/60 p-5">
          <h4 className="text-lg font-black text-slate-900">
            B. Validar Word y Excel
          </h4>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            El sistema comprobará que no falte ninguna etiqueta y que
            cada etiqueta identifique un único lugar.
          </p>

          <div className="mt-5">
            <FileInput
              label="Word incompleto con etiquetas"
              name="tagged_word_v2"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              required
              helperText="Documento avanzado que contiene etiquetas como {{PENDIENTE_LIBERTAD_PISO_3}}."
              onChange={handleWordChange}
            />
          </div>

          <button
            type="button"
            onClick={handleValidate}
            disabled={!canValidate || validating}
            className="mt-5 w-full rounded-2xl border border-violet-300 bg-white px-5 py-4 text-sm font-black text-violet-700 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          >
            {validating
              ? "Validando etiquetas..."
              : "Validar Word contra Excel"}
          </button>
        </article>
      </div>

      {validation && (
        <ValidationPanel
          key={`${selectedFilesChanged.excel}-${selectedFilesChanged.word}`}
          validation={validation}
        />
      )}

      <article className="mt-6 rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white md:p-6">
        <h4 className="text-xl font-black">
          C. Generar documento completo
        </h4>

        <p className="mt-2 text-sm leading-6 text-slate-300">
          Coloca las fotografías dentro del ZIP generado, vuelve a
          comprimir la estructura y selecciónala aquí.
        </p>

        <div className="mt-5 rounded-2xl bg-white p-1 text-slate-900">
          <FileInput
            label="ZIP con fotografías por etiqueta"
            name="tagged_evidence_zip_v2"
            accept=".zip,application/zip,application/x-zip-compressed"
            required
            helperText="ZIP de carpetas que ya contiene las fotografías pendientes."
            onChange={setEvidenceZip}
          />
        </div>

        {!validation?.compatible && (
          <p className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-xs leading-5 text-amber-200">
            Primero valida el Word contra el Excel. El botón se
            habilitará cuando todas las etiquetas coincidan.
          </p>
        )}

        <button
          type="button"
          onClick={handleGenerateDocument}
          disabled={!canGenerate || generatingDocument}
          className="mt-5 w-full rounded-2xl bg-violet-500 px-6 py-4 text-sm font-black text-white shadow-xl transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {generatingDocument
            ? "Completando documento Word..."
            : "Descargar documento completo"}
        </button>
      </article>
    </section>
  );
}