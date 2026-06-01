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
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-amber-300 focus:px-4 focus:py-2 focus:text-stone-950"
      >
        {content.skipLink}
      </a>

      <Header content={content} language={language} onLanguageChange={setLanguage} />

      <main id="main-content" className="mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:px-6 lg:px-8" role="main">
        <HeroSection content={content} />
        <StorySection content={content} />
        <UniqueSection content={content} />
        <LocationsSection content={content} />
        <MenuSection content={content} />
        <BrasaPointsSection content={content} />
        <ContactSection content={content} />
      </main>

      <Footer content={content} />
    </>
  );
}
