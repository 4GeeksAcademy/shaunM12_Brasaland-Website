"use client";

import { useEffect, useMemo, useState } from "react";

import { MenuCatalog } from "@/components/menu/MenuCatalog";
import { MenuPageHeader } from "@/components/menu/MenuPageHeader";
import { translations, type SupportedLanguage } from "@/lib/home-content";

const LANGUAGE_STORAGE_KEY = "brasaland_lang";

export function MenuPage(): React.JSX.Element {
  const [language, setLanguage] = useState<SupportedLanguage>("en");

  useEffect(() => {
    const savedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);

    if (savedLanguage === "en" || savedLanguage === "es") {
      setLanguage(savedLanguage);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }, [language]);

  const content = useMemo(() => translations[language], [language]);

  return (
    <div className="site-shell menu-page-shell">
      <MenuPageHeader
        content={content}
        language={language}
        onLanguageChange={setLanguage}
      />
      <main className="site-container menu-page-main pb-16 pt-6 sm:pt-8">
        <MenuCatalog language={language} />
      </main>
    </div>
  );
}
