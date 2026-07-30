"use client";

import { useEffect, useMemo, useState } from "react";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { HeroSection } from "./HeroSection";
import { StorySection } from "./StorySection";
import { UniqueSection } from "./UniqueSection";
import { LocationsSection } from "./LocationsSection";
import { MenuSection } from "./MenuSection";
import { BrasaPointsSection } from "./BrasaPointsSection";
import { ContactSection } from "./ContactSection";
import { translations } from "@/lib/home-content";
import type { SupportedLanguage } from "@/lib/home-content";

const LANGUAGE_STORAGE_KEY = "brasaland_lang";

export function HomePage(): React.JSX.Element {
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
    <div className="site-shell">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-full focus:bg-[var(--brand-yellow)] focus:px-4 focus:py-2 focus:font-bold focus:text-[#17130a]"
      >
        {content.skipLink}
      </a>

      <Header content={content} language={language} onLanguageChange={setLanguage} />

      <main id="main-content" className="site-container pb-16 pt-4 sm:pb-20 sm:pt-8" role="main">
        <HeroSection content={content} />
        <StorySection content={content} />
        <UniqueSection content={content} />
        <LocationsSection content={content} />
        <MenuSection content={content} />
        <BrasaPointsSection content={content} />
        <ContactSection content={content} />
      </main>

      <Footer content={content} />
    </div>
  );
}
