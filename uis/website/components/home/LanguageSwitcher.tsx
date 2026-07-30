import type { SupportedLanguage } from "@/lib/home-content";

interface LanguageSwitcherProps {
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
  ariaLabel: string;
}

export function LanguageSwitcher({
  language,
  onLanguageChange,
  ariaLabel,
}: LanguageSwitcherProps): React.JSX.Element {
  return (
    <div className="control-pill" role="group" aria-label={ariaLabel}>
      {(["es", "en"] as const).map((nextLanguage) => {
        const isActive = nextLanguage === language;

        return (
          <button
            key={nextLanguage}
            type="button"
            onClick={() => onLanguageChange(nextLanguage)}
            aria-pressed={isActive}
            className={`language-button ${isActive ? "language-button-active" : ""}`}
          >
            {nextLanguage.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
