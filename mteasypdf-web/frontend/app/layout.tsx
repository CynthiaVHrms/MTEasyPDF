import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title:  "M.I.A Modulo de Informacion y Anexos",
  description: "Generador web de memorias técnicas HEMAC",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
