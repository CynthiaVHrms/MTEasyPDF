"use client";

export type MissingImageDiagnostic = {
  etiqueta?: string;
  seccion?: string;
  subseccion?: string;
  evidencia?: string;
  titulo?: string;
  motivo?: string;
};

export type OmittedImageDiagnostic = MissingImageDiagnostic & {
  archivo?: string;
};

export type MissingTagDiagnostic = {
  etiqueta?: string;
  seccion?: string;
  subseccion?: string;
  motivo?: string;
};

export type DocumentDiagnosticsData = {
  job_id?: string;
  estado?: string;
  resumen: {
    etiquetas_totales?: number;
    etiquetas_reemplazadas?: number;
    etiquetas_no_encontradas?: number;
    imagenes_insertadas?: number;
    imagenes_no_encontradas?: number;
    imagenes_omitidas_por_dano?: number;
  };
  imagenes_no_encontradas?: MissingImageDiagnostic[];
  imagenes_omitidas?: OmittedImageDiagnostic[];
  etiquetas_no_encontradas?: MissingTagDiagnostic[];
};

type Props = {
  diagnostics: DocumentDiagnosticsData;
  title?: string;
  description?: string;
};

function MetricCard({ label, value, tone }: { label: string; value: number; tone: "slate" | "amber" | "rose" | "violet" }) {
  const toneClasses = {
    slate: "border-slate-200 bg-slate-50 text-slate-950",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
    rose: "border-rose-200 bg-rose-50 text-rose-950",
    violet: "border-violet-200 bg-violet-50 text-violet-950",
  };

  return (
    <div className={`rounded-2xl border p-4 ${toneClasses[tone]}`}>
      <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-black">{value}</p>
    </div>
  );
}

export function DocumentDiagnostics({ diagnostics, title = "Documento completado", description }: Props) {
  const inserted = diagnostics.resumen.imagenes_insertadas ?? 0;
  const missing = diagnostics.resumen.imagenes_no_encontradas ?? 0;
  const omitted = diagnostics.resumen.imagenes_omitidas_por_dano ?? 0;
  const pendingTags = diagnostics.resumen.etiquetas_no_encontradas ?? 0;
  const hasObservations = missing > 0 || omitted > 0 || pendingTags > 0;

  return (
    <section className={`overflow-hidden rounded-3xl border ${hasObservations ? "border-amber-200 bg-white" : "border-emerald-200 bg-white"}`}>
      <header className={`flex items-start gap-4 border-b p-5 ${hasObservations ? "border-amber-200 bg-amber-50" : "border-emerald-200 bg-emerald-50"}`}>
        <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-lg font-black text-white ${hasObservations ? "bg-amber-500" : "bg-emerald-600"}`}>
          {hasObservations ? "!" : "✓"}
        </span>
        <div>
          <h4 className="text-lg font-black text-slate-950">
            {hasObservations ? `${title} con observaciones` : `${title} sin observaciones`}
          </h4>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {description ?? (hasObservations
              ? "El archivo se descargó correctamente. Revisa los detalles antes de entregarlo."
              : "Todas las etiquetas fueron reemplazadas y las evidencias disponibles se insertaron correctamente.")}
          </p>
        </div>
      </header>

      <div className="p-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Imágenes insertadas" value={inserted} tone="slate" />
          <MetricCard label="No encontradas" value={missing} tone="amber" />
          <MetricCard label="Omitidas por daño" value={omitted} tone="rose" />
          <MetricCard label="Etiquetas pendientes" value={pendingTags} tone="violet" />
        </div>

        <div className="mt-5 space-y-3">
          {(diagnostics.imagenes_no_encontradas?.length ?? 0) > 0 && (
            <details className="group rounded-2xl border border-amber-200 bg-amber-50/60">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-amber-950">
                <span>Ver imágenes no encontradas ({diagnostics.imagenes_no_encontradas?.length})</span>
                <span className="transition group-open:rotate-180">⌄</span>
              </summary>
              <div className="max-h-72 space-y-3 overflow-y-auto border-t border-amber-200 p-4">
                {diagnostics.imagenes_no_encontradas?.map((item, index) => (
                  <article key={`${item.etiqueta}-${item.evidencia}-${index}`} className="rounded-xl border border-amber-100 bg-white p-4 text-sm">
                    <p className="font-black text-slate-950">Evidencia {item.evidencia || "sin nombre"}</p>
                    <p className="mt-1 text-slate-600"><strong>Etiqueta:</strong> {item.etiqueta || "No indicada"}</p>
                    <p className="text-slate-600"><strong>Sección:</strong> {item.seccion || "No indicada"}</p>
                    {item.subseccion && <p className="text-slate-600"><strong>Subsección:</strong> {item.subseccion}</p>}
                    {item.motivo && <p className="mt-2 text-amber-800">{item.motivo}</p>}
                  </article>
                ))}
              </div>
            </details>
          )}

          {(diagnostics.imagenes_omitidas?.length ?? 0) > 0 && (
            <details className="group rounded-2xl border border-rose-200 bg-rose-50/60">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-rose-950">
                <span>Ver imágenes omitidas por daño ({diagnostics.imagenes_omitidas?.length})</span>
                <span className="transition group-open:rotate-180">⌄</span>
              </summary>
              <div className="max-h-72 space-y-3 overflow-y-auto border-t border-rose-200 p-4">
                {diagnostics.imagenes_omitidas?.map((item, index) => (
                  <article key={`${item.archivo}-${index}`} className="rounded-xl border border-rose-100 bg-white p-4 text-sm">
                    <p className="font-black text-slate-950">{item.archivo || item.evidencia || "Imagen dañada"}</p>
                    <p className="mt-1 text-slate-600"><strong>Etiqueta:</strong> {item.etiqueta || "No indicada"}</p>
                    {item.motivo && <p className="mt-2 text-rose-800">{item.motivo}</p>}
                  </article>
                ))}
              </div>
            </details>
          )}

          {(diagnostics.etiquetas_no_encontradas?.length ?? 0) > 0 && (
            <details className="group rounded-2xl border border-violet-200 bg-violet-50/60">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-violet-950">
                <span>Ver etiquetas no reemplazadas ({diagnostics.etiquetas_no_encontradas?.length})</span>
                <span className="transition group-open:rotate-180">⌄</span>
              </summary>
              <div className="max-h-72 space-y-3 overflow-y-auto border-t border-violet-200 p-4">
                {diagnostics.etiquetas_no_encontradas?.map((item, index) => (
                  <article key={`${item.etiqueta}-${index}`} className="rounded-xl border border-violet-100 bg-white p-4 text-sm">
                    <code className="font-black text-violet-900">{`{{${item.etiqueta || "ETIQUETA"}}}`}</code>
                    <p className="mt-2 text-slate-600"><strong>Sección:</strong> {item.seccion || "No indicada"}</p>
                    {item.motivo && <p className="mt-2 text-violet-800">{item.motivo}</p>}
                  </article>
                ))}
              </div>
            </details>
          )}
        </div>
      </div>
    </section>
  );
}