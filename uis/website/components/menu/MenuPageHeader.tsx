import Link from "next/link";

import type { TranslationDictionary } from "@/lib/home-content";
import type { SupportedLanguage } from "@/lib/home-content";

import { LanguageSwitcher } from "@/components/home/LanguageSwitcher";
import { ThemeToggle } from "@/components/home/ThemeToggle";

interface MenuPageHeaderProps {
  content: TranslationDictionary;
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
}

export function MenuPageHeader({
  content,
  language,
  onLanguageChange,
}: MenuPageHeaderProps): React.JSX.Element {
  return (
    <header className="site-header" role="banner">
      <div className="site-container site-header-bar">
        <Link href="/" className="menu-page-brand brand-display text-3xl tracking-wide sm:text-4xl">
          Brasaland
        </Link>

        <div className="site-header-actions">
          <LanguageSwitcher
            language={language}
            onLanguageChange={onLanguageChange}
            ariaLabel={content.languageSelector}
          />
          <ThemeToggle
            lightLabel={content.themeLight}
            darkLabel={content.themeDark}
            switchToLightLabel={content.themeSwitchToLight}
            switchToDarkLabel={content.themeSwitchToDark}
          />
        </div>
      </div>
      <div className="site-container pb-3">
        <Link href="/" className="menu-page-back">
          ← {content.menuBackToHome}
        </Link>
      </div>
    </header>
  );
}
