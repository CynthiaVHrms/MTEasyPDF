import { AppShell } from "@/components/AppShell";
import { AuthCheck } from "./auth-check";

type Module = "mteasy" | "c5" | "docs";

function resolveModule(value: string | string[] | undefined): Module {
  const raw = Array.isArray(value) ? value[0] : value;

  if (raw === "c5" || raw === "docs" || raw === "mteasy") {
    return raw;
  }

  return "mteasy";
}

export default async function Home({
  searchParams,
}: {
  searchParams?:
    | Record<string, string | string[] | undefined>
    | Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await Promise.resolve(searchParams ?? {});
  const initialModule = resolveModule(params.module);

  return (
    <>
      <AuthCheck />
      <AppShell initialModule={initialModule} />
    </>
  );
}

