export type GenerationProgressView = {
  status: "uploading" | "queued" | "processing" | "completed" | "failed";
  stage: string;
  percentage: number;
  message: string;
  current_site: number;
  total_sites: number;
  current_site_name: string;
  processed_images: number;
  total_images: number;
  detected_images: number;
  error?: string | null;
};

type GenerationProgressProps = {
  progress: GenerationProgressView;
};

const STAGES = [
  {
    key: "files",
    label: "Archivos",
    stages: ["uploading", "queued", "validating_files", "preparing_workspace"],
  },
  {
    key: "zip",
    label: "ZIP",
    stages: ["extracting_zip"],
  },
  {
    key: "excel",
    label: "Plantilla",
    stages: ["reading_excel", "analyzing_evidence"],
  },
  {
    key: "evidence",
    label: "Evidencias",
    stages: ["processing_sites"],
  },
  {
    key: "document",
    label: "Documento",
    stages: ["writing_diagnostics", "assembling_document", "saving_document"],
  },
  {
    key: "ready",
    label: "Listo",
    stages: ["completed"],
  },
] as const;

function getCurrentStageIndex(stage: string): number {
  const index = STAGES.findIndex((item) =>
    item.stages.some((stageName) => stageName === stage),
  );

  return index >= 0 ? index : 0;
}

export function GenerationProgress({ progress }: GenerationProgressProps) {
  const percentage = Math.max(0, Math.min(100, Math.round(progress.percentage)));
  const currentStageIndex = getCurrentStageIndex(progress.stage);
  const isCompleted = progress.status === "completed";
  const isFailed = progress.status === "failed";

  const containerClasses = isFailed
    ? "border-rose-200 bg-rose-50"
    : isCompleted
      ? "border-emerald-200 bg-emerald-50"
      : "border-blue-200 bg-blue-50/70";

  const accentClasses = isFailed
    ? "bg-rose-600"
    : isCompleted
      ? "bg-emerald-600"
      : "bg-blue-600";

  const title = isFailed
    ? "La generación necesita atención"
    : isCompleted
      ? "Documento listo"
      : progress.status === "uploading"
        ? "Enviando archivos"
        : "Generando protocolo C5";

  return (
    <section
      className={`mt-5 overflow-hidden rounded-3xl border p-5 shadow-sm ${containerClasses}`}
      aria-live="polite"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-white ${accentClasses}`}
          >
            {isFailed ? (
              <span className="text-lg font-black">!</span>
            ) : isCompleted ? (
              <span className="text-lg font-black">✓</span>
            ) : (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            )}
          </div>

          <div className="min-w-0">
            <h4 className="text-base font-black text-slate-950">{title}</h4>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              {isFailed && progress.error ? progress.error : progress.message}
            </p>
          </div>
        </div>

        <div className="rounded-2xl bg-white/80 px-4 py-2 text-right shadow-sm ring-1 ring-slate-200/70">
          <p className="text-2xl font-black tabular-nums text-slate-950">
            {percentage}%
          </p>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Avance real
          </p>
        </div>
      </div>

      <div className="mt-5">
        <div
          className="h-3 overflow-hidden rounded-full bg-white shadow-inner ring-1 ring-slate-200"
          role="progressbar"
          aria-label="Progreso de generación del documento Word"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percentage}
        >
          <div
            className={`h-full rounded-full transition-[width] duration-500 ease-out ${accentClasses}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {!isFailed && (
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {STAGES.map((item, index) => {
            const stageCompleted = isCompleted || index < currentStageIndex;
            const stageCurrent = !isCompleted && index === currentStageIndex;

            return (
              <div
                key={item.key}
                className={`flex min-h-24 min-w-0 flex-col items-center justify-center rounded-2xl border px-3 py-4 text-center transition ${
                  stageCompleted
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : stageCurrent
                      ? "border-blue-200 bg-white text-blue-800 shadow-sm"
                      : "border-slate-200 bg-white/60 text-slate-400"
                }`}
              >
                <div className="mx-auto flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black">
                  {stageCompleted ? "✓" : stageCurrent ? "●" : "○"}
                </div>
                <p className="mt-2 w-full break-words text-xs font-bold leading-4">
                  {item.label}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {!isCompleted && !isFailed && (
        <p className="mt-4 text-center text-xs font-semibold text-slate-500">
          El proceso continúa normalmente. No cierres esta ventana.
        </p>
      )}
    </section>
  );
}
