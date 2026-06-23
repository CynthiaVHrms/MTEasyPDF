import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title:  "MTEasyPDF Web",
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
