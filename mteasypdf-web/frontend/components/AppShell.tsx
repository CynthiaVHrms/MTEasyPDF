"use client";

import { useState } from "react";
import { ReportForm } from "@/features/reports/ReportForm";
import { ProtocolsSection } from "@/features/protocols/ProtocolsSection";
import { DocumentationCard } from "@/components/DocumentationCard";

type Module = "mteasy" | "c5" | "docs";

const modules = [
  {
    id: "mteasy" as const,
    icon: "📄",
    title: "Memoria Técnica",
    description: "Generar PDF y ZIP final",
  },
  {
    id: "c5" as const,
    icon: "🛡️",
    title: "Protocolos C5",
    description: "Carpetas y documento Word",
  },
  {
    id: "docs" as const,
    icon: "📘",
    title: "Manual de Usuario",
    description: "Guía de operación",
  },
];

export function AppShell() {
  const [activeModule, setActiveModule] = useState<Module>("mteasy");

  return (
    <main className="min-h-screen bg-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="mb-6 rounded-[2rem] bg-linear-to-r from-blue-700 to-slate-950 px-8 py-8 text-white shadow-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-blue-100">
            HEMAC Automation Engine
          </p>
          <h1 className="mt-3 text-4xl font-bold">MTEasyPDF Web</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-100">
            Plataforma interna para generación documental, Memorias Técnicas y
            automatización de Protocolos C5.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <aside className="h-fit rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-400">
              Módulos
            </p>

            <nav className="mt-5 space-y-3">
              {modules.map((module) => {
                const active = activeModule === module.id;

                return (
                  <button
                    key={module.id}
                    type="button"
                    onClick={() => setActiveModule(module.id)}
                    className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                      active
                        ? "border-blue-500 bg-blue-50 shadow-sm"
                        : "border-slate-200 bg-white hover:border-blue-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-11 w-11 items-center justify-center rounded-xl text-xl ${
                          active
                            ? "bg-blue-600 text-white"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {module.icon}
                      </div>

                      <div>
                        <p className="font-bold text-slate-900">
                          {module.title}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {module.description}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </nav>

            <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
              <p className="text-sm font-bold text-emerald-800">
                MTEasyPDF Web v1.0.0
              </p>
              <p className="mt-1 text-xs text-emerald-700">
                FastAPI · Next.js · HEMAC
              </p>
            </div>
          </aside>

          <section>
            {activeModule === "mteasy" && <ReportForm />}
            {activeModule === "c5" && <ProtocolsSection />}
            {activeModule === "docs" && <DocumentationCard />}
          </section>
        </div>
      </div>
    </main>
  );
}