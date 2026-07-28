"use client";

import { useTheme } from "@/context/ThemeProvider";

export default function ThemeToggle(): React.JSX.Element {
  const { theme, toggleTheme } = useTheme();
  const label = theme === "dark" ? "Light mode" : "Dark mode";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className="rounded-full border border-[color:var(--bo-accent-border)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--bo-accent)] transition hover:bg-[color:var(--bo-accent-soft)]"
    >
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
