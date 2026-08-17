"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "mia-theme";

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const isDark = theme === "dark";

  root.classList.toggle("dark", isDark);
  root.style.colorScheme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const currentTheme: Theme =
      document.documentElement.classList.contains("dark")
        ? "dark"
        : "light";

    setTheme(currentTheme);
    setMounted(true);
  }, []);

  function handleToggle() {
    const nextTheme: Theme =
      theme === "dark"
        ? "light"
        : "dark";

    setTheme(nextTheme);
    applyTheme(nextTheme);

    try {
      window.localStorage.setItem(
        THEME_STORAGE_KEY,
        nextTheme
      );
    } catch {
      /*
       * Si el navegador bloquea localStorage,
       * el cambio de tema continúa funcionando
       * durante la sesión actual.
       */
    }
  }

  const isDark = theme === "dark";

  const label = isDark
    ? "Cambiar a tema claro"
    : "Cambiar a tema oscuro";

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label={label}
      title={label}
      className="
        absolute
        right-5
        top-5
        inline-flex
        min-h-11
        items-center
        gap-2
        rounded-2xl
        border
        border-white/20
        bg-white/10
        px-3.5
        py-2.5
        text-sm
        font-bold
        text-white
        shadow-lg
        backdrop-blur-md
        transition
        hover:border-white/35
        hover:bg-white/20
        focus-visible:outline-none
        focus-visible:ring-4
        focus-visible:ring-white/20
        md:right-7
        md:top-7
        md:px-4
      "
    >
      <span
        aria-hidden="true"
        className="
          flex
          h-7
          w-7
          items-center
          justify-center
          rounded-xl
          bg-white/15
          text-base
        "
      >
        {mounted
          ? isDark
            ? "☀️"
            : "🌙"
          : "◐"}
      </span>

      <span className="hidden sm:inline">
        {mounted
          ? isDark
            ? "Tema claro"
            : "Tema oscuro"
          : "Tema"}
      </span>
    </button>
  );
}