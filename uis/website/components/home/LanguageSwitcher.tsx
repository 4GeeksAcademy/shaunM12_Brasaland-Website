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
    <div className="order-2 flex items-center gap-2 lg:order-3" role="group" aria-label={ariaLabel}>
      {(["es", "en"] as const).map((nextLanguage) => {
        const isActive = nextLanguage === language;

        return (
          <button
            key={nextLanguage}
            type="button"
            onClick={() => onLanguageChange(nextLanguage)}
            aria-pressed={isActive}
            className={`rounded-full border px-3 py-1 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300 ${
              isActive
                ? "border-amber-300 text-amber-300"
                : "border-stone-500 text-stone-100 hover:border-amber-300 hover:text-amber-300"
            }`}
          >
            {nextLanguage.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
