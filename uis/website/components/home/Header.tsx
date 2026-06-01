import type { TranslationDictionary } from "@/lib/home-content";
import type { SupportedLanguage } from "@/lib/home-content";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { BrandLogo } from "./BrandLogo";

interface HeaderProps {
  content: TranslationDictionary;
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
}

export function Header({ content, language, onLanguageChange }: HeaderProps): React.JSX.Element {
  return (
    <header className="sticky top-0 z-40 border-b border-amber-200/10 bg-stone-950/95 backdrop-blur" role="banner">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <BrandLogo tagline={content.brandTagline} />

        <nav className="order-3 lg:order-2" aria-label={content.navPrimary}>
          <ul className="flex flex-wrap gap-3 text-sm font-semibold sm:gap-5 sm:text-base">
            <li>
              <a className="rounded px-2 py-1 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300" href="#home">
                {content.navHome}
              </a>
            </li>
            <li>
              <a className="rounded px-2 py-1 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300" href="#locations">
                {content.navLocations}
              </a>
            </li>
            <li>
              <a className="rounded px-2 py-1 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300" href="#menu">
                {content.navMenu}
              </a>
            </li>
            <li>
              <a className="rounded px-2 py-1 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300" href="#brasa-points">
                {content.navBrasaPoints}
              </a>
            </li>
            <li>
              <a className="rounded px-2 py-1 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300" href="#contact">
                {content.navContact}
              </a>
            </li>
          </ul>
        </nav>

        <LanguageSwitcher
          language={language}
          onLanguageChange={onLanguageChange}
          ariaLabel={content.languageSelector}
        />
      </div>
    </header>
  );
}
