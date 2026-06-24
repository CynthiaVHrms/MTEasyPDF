export function DocumentationCard() {
  return (
    <section className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-600">
          Centro de Documentación
        </p>

        <h2 className="mt-2 text-2xl font-bold text-slate-900">
          Recursos del sistema
        </h2>

        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
          Consulta y descarga la información necesaria para utilizar MTEasyPDF
          Web correctamente.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-2xl text-white">
              📘
            </div>

            <div className="flex-1">
              <h3 className="text-base font-bold text-slate-900">
                Manual de Usuario
              </h3>

              <p className="mt-1 text-sm leading-6 text-slate-600">
                Guía paso a paso para generar Memorias Técnicas, descargar el
                ZIP final y abrir los anexos correctamente.
              </p>

              <a
                href="/docs/Manual de Usuario MTEasy.pdf"
                download
                className="mt-4 inline-flex rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700"
              >
                Descargar manual PDF
              </a>
            </div>
          </div>
        </article>

        {/* <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-700 text-2xl text-white">
              📚
            </div>

            <div className="flex-1">
              <h3 className="text-base font-bold text-slate-900">
                Documentación Técnica
              </h3>

              <p className="mt-1 text-sm leading-6 text-slate-600">
                Arquitectura, estructura del proyecto, backend, frontend,
                motor PDF y decisiones técnicas.
              </p>

              <a
                href="/docs/TECHNICAL_DOCUMENTATION.md"
                target="_blank"
                className="mt-4 inline-flex rounded-xl bg-slate-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-slate-800"
              >
                Ver documentación
              </a>
            </div>
          </div>
        </article> */}
      </div>

      <div className="mt-6 rounded-2xl border border-emerald-100 bg-emerald-50 px-5 py-4">
        <p className="text-sm font-bold text-emerald-800">
          MTEasyPDF Web v1.0.0
        </p>
        <p className="mt-1 text-xs text-emerald-700">
          HEMAC Automation Engine · Backend FastAPI · Frontend Next.js
        </p>
      </div>
    </section>
  );
}