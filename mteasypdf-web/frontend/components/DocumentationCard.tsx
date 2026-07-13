export function DocumentationCard() {
  return (
    <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.25em] text-blue-600">
        Manual de Usuario
      </p>

      <h2 className="mt-2 text-3xl font-bold text-slate-900">
        Centro de ayuda
      </h2>

      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
        Descarga la guía oficial para utilizar MTEasyPDF Web paso a paso.
      </p>

      <div className="mt-6 rounded-3xl border border-blue-100 bg-blue-50 p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-2xl text-white">
              📘
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-900">
                Manual de Usuario
              </h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Guía sencilla para generar Memorias Técnicas, descargar el ZIP
                final, extraer los archivos y abrir correctamente los anexos.
              </p>
            </div>
          </div>

          <a
            href="/docs/Manual de Usuario MTEasy.pdf"
            download
            className="inline-flex justify-center rounded-2xl bg-blue-700 px-6 py-4 text-sm font-bold text-white shadow-lg transition hover:bg-blue-800"
          >
            Descargar manual PDF
          </a>
        </div>
      </div>
    </section>
  );
}
