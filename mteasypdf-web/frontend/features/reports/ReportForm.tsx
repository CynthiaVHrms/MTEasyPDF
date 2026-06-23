"use client";

import { useState } from "react";
import { FileInput } from "@/components/FileInput";
import { TextInput } from "@/components/TextInput";

import {
  buildDownloadUrl,
  generateReport,
  GenerateReportResponse,
} from "./reportApi";


export function ReportForm() {
  const [titulo, setTitulo] = useState("");
  const [infoExtra, setInfoExtra] = useState("");
  const [introduccion, setIntroduccion] = useState("");
  const [usaUbicacion, setUsaUbicacion] = useState(true);

  const [imagenPortada, setImagenPortada] = useState<File | null>(null);
  const [logo1, setLogo1] = useState<File | null>(null);
  const [logo2, setLogo2] = useState<File | null>(null);
  const [logo3, setLogo3] = useState<File | null>(null);
  const [evidenciasZip, setEvidenciasZip] = useState<File | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateReportResponse | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setResult(null);

    if (!evidenciasZip) {
      setError("Debes seleccionar el ZIP de evidencias.");
      return;
    }

    const formData = new FormData();

    formData.append("titulo", titulo);
    formData.append("info_extra", infoExtra);
    formData.append("introduccion", introduccion);
    formData.append("usa_ubicacion", String(usaUbicacion));
    formData.append("evidencias_zip", evidenciasZip);

    if (imagenPortada) formData.append("imagen_portada", imagenPortada);
    if (logo1) formData.append("logo1", logo1);
    if (logo2) formData.append("logo2", logo2);
    if (logo3) formData.append("logo3", logo3);

    try {
      setIsGenerating(true);
      const response = await generateReport(formData);
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Ocurrió un error inesperado generando el reporte."
      );
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 rounded-3xl bg-gradient-to-r from-blue-700 to-slate-900 px-8 py-10 text-white shadow-xl">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-100">
          HEMAC Automation Engine
        </p>
        <h1 className="mt-3 text-4xl font-bold">MTEasyPDF Web</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-100">
          Generador web de memoria técnica. Carga la evidencia, captura los
          datos del proyecto y descarga el ZIP final con el reporte principal y
          anexos.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]"
      >
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-slate-900">
            Datos del proyecto
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Información que aparecerá dentro de la memoria técnica.
          </p>

          <div className="mt-6 space-y-5">
            <TextInput
              label="Título"
              name="titulo"
              value={titulo}
              required
              placeholder="Ej. Memoria Técnica - Mantenimiento"
              onChange={setTitulo}
            />

            <TextInput
              label="Información extra"
              name="info_extra"
              value={infoExtra}
              placeholder="Ej. Cliente, sede, periodo o folio"
              onChange={setInfoExtra}
            />

            <TextInput
              label="Introducción"
              name="introduccion"
              value={introduccion}
              multiline
              placeholder="Escribe la introducción del reporte..."
              onChange={setIntroduccion}
            />

            <label className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <span className="block text-sm font-semibold text-slate-800">
                  Incluir sección de ubicación
                </span>
                <span className="text-xs text-slate-500">
                  Mantiene la lógica actual del reporte de escritorio.
                </span>
              </div>

              <input
                type="checkbox"
                checked={usaUbicacion}
                onChange={(event) => setUsaUbicacion(event.target.checked)}
                className="h-5 w-5 rounded border-slate-300 text-blue-600"
              />
            </label>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-slate-900">
            Archivos del reporte
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Sube portada, logos y el ZIP de evidencias.
          </p>

          <div className="mt-6 space-y-4">
            <FileInput
              label="Imagen de portada"
              name="imagen_portada"
              accept="image/png,image/jpeg"
              helperText="Opcional. Formato PNG o JPG."
              onChange={setImagenPortada}
            />

            <FileInput
              label="Logo 1"
              name="logo1"
              accept="image/png,image/jpeg"
              helperText="Opcional."
              onChange={setLogo1}
            />

            <FileInput
              label="Logo 2"
              name="logo2"
              accept="image/png,image/jpeg"
              helperText="Opcional."
              onChange={setLogo2}
            />

            <FileInput
              label="Logo 3"
              name="logo3"
              accept="image/png,image/jpeg"
              helperText="Opcional."
              onChange={setLogo3}
            />

            <FileInput
              label="ZIP de evidencias"
              name="evidencias_zip"
              required
              accept=".zip,application/zip,application/x-zip-compressed"
              helperText="Obligatorio. Puede contener imágenes, PDFs e inventario."
              onChange={setEvidenciasZip}
            />
          </div>
        </section>

        <section className="lg:col-span-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            {error && (
              <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                {error}
              </div>
            )}

            {result && (
              <div className="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4">
                <p className="text-sm font-bold text-emerald-800">
                  Reporte generado correctamente
                </p>
                <p className="mt-1 text-xs text-emerald-700">
                  Job ID: {result.job_id}
                </p>

                <a
                  href={buildDownloadUrl(result.download_url)}
                  className="mt-4 inline-flex rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-700"
                >
                  Descargar ZIP final
                </a>
              </div>
            )}

            <button
              type="submit"
              disabled={isGenerating}
              className="flex w-full items-center justify-center rounded-2xl bg-blue-700 px-6 py-4 text-base font-bold text-white shadow-lg transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isGenerating
                ? "Generando memoria técnica..."
                : "Generar memoria técnica"}
            </button>

            <p className="mt-3 text-center text-xs text-slate-500">
              No cierres esta ventana mientras se genera el reporte.
            </p>
          </div>
        </section>
      </form>
    </div>
  );
}