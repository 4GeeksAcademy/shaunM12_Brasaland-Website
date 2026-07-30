"use client";

import { useTheme } from "@/context/ThemeProvider";

export default function ThemeToggle(): React.JSX.Element {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const label = isDark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className="bo-theme-toggle"
    >
      <span className="bo-theme-toggle-track" aria-hidden="true">
        <span className="bo-theme-toggle-thumb">
          {isDark ? (
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5">
              <path
                d="M20.4 15.4A8.5 8.5 0 0 1 8.6 3.6 8.5 8.5 0 1 0 20.4 15.4Z"
                fill="currentColor"
              />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5">
              <circle cx="12" cy="12" r="4" fill="currentColor" />
              <path
                d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeWidth="2"
              />
            </svg>
          )}
        </span>
      </span>
      <span className="hidden sm:inline">{isDark ? "Dark" : "Light"}</span>
    </button>
  );
}
