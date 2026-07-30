"use client";

import { useTheme } from "@/context/ThemeProvider";

interface ThemeToggleProps {
  lightLabel: string;
  darkLabel: string;
  switchToLightLabel: string;
  switchToDarkLabel: string;
}

export function ThemeToggle({
  lightLabel,
  darkLabel,
  switchToLightLabel,
  switchToDarkLabel,
}: ThemeToggleProps): React.JSX.Element {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const label = isDark ? switchToLightLabel : switchToDarkLabel;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className="theme-toggle"
    >
      <span className="theme-toggle-track" aria-hidden="true">
        <span className="theme-toggle-thumb">
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
      <span className="hidden text-xs font-bold uppercase tracking-[0.12em] sm:inline">
        {isDark ? darkLabel : lightLabel}
      </span>
    </button>
  );
}
