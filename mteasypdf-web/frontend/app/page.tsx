import { AppShell } from "@/components/AppShell";
import { AuthCheck } from "./auth-check";

export default function Home(){
  return (
    <>
      <AuthCheck />
      <AppShell />
    </>
  );
}

