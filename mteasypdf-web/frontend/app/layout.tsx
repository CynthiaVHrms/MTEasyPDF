import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "M.I.A Modulo de Informacion y Anexos",
  description: "Generador web de memorias técnicas HEMAC",
};

const themeInitializer = `
(function () {
  try {
    var storedTheme = localStorage.getItem("mia-theme");

    var prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)"
    ).matches;

    var useDark =
      storedTheme === "dark" ||
      (storedTheme !== "light" && prefersDark);

    document.documentElement.classList.toggle(
      "dark",
      useDark
    );

    document.documentElement.style.colorScheme =
      useDark ? "dark" : "light";
  } catch (error) {
    document.documentElement.classList.remove("dark");
    document.documentElement.style.colorScheme = "light";
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: themeInitializer,
          }}
        />
      </head>

      <body>
        {children}
      </body>
    </html>
  );
}