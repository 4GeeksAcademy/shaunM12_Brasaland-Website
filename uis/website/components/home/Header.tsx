"use client";

import { useEffect, useId, useState } from "react";

import type { SupportedLanguage, TranslationDictionary } from "@/lib/home-content";

import { BrandLogo } from "./BrandLogo";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  content: TranslationDictionary;
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
}

interface NavItem {
  href: string;
  label: string;
}

function buildNavItems(content: TranslationDictionary): NavItem[] {
  return [
    { href: "#home", label: content.navHome },
    { href: "#locations", label: content.navLocations },
    { href: "#menu", label: content.navMenu },
    { href: "#brasa-points", label: content.navBrasaPoints },
    { href: "#contact", label: content.navContact },
  ];
}

export function Header({ content, language, onLanguageChange }: HeaderProps): React.JSX.Element {
  const [menuOpen, setMenuOpen] = useState(false);
  const mobileNavId = useId();
  const navItems = buildNavItems(content);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const closeOnDesktop = (): void => {
      if (mediaQuery.matches) {
        setMenuOpen(false);
      }
    };

    mediaQuery.addEventListener("change", closeOnDesktop);
    return () => mediaQuery.removeEventListener("change", closeOnDesktop);
  }, []);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    const closeOnEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);

  function closeMenu(): void {
    setMenuOpen(false);
  }

  return (
    <header className="site-header" role="banner">
      <div className="site-container site-header-bar">
        <BrandLogo tagline={content.brandTagline} />

        <nav className="site-nav-desktop" aria-label={content.navPrimary}>
          <ul className="site-nav-list">
            {navItems.map((item) => (
              <li key={item.href}>
                <a className="site-nav-link" href={item.href}>
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

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
          <button
            type="button"
            className="site-nav-toggle"
            aria-expanded={menuOpen}
            aria-controls={mobileNavId}
            aria-label={menuOpen ? content.navCloseMenu : content.navOpenMenu}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="site-nav-toggle-bars" aria-hidden="true">
              <span className={menuOpen ? "site-nav-toggle-bar site-nav-toggle-bar-top-open" : "site-nav-toggle-bar site-nav-toggle-bar-top"} />
              <span className={menuOpen ? "site-nav-toggle-bar site-nav-toggle-bar-middle-open" : "site-nav-toggle-bar"} />
              <span className={menuOpen ? "site-nav-toggle-bar site-nav-toggle-bar-bottom-open" : "site-nav-toggle-bar site-nav-toggle-bar-bottom"} />
            </span>
          </button>
        </div>
      </div>

      <nav
        id={mobileNavId}
        className={menuOpen ? "site-mobile-nav site-mobile-nav-open" : "site-mobile-nav"}
        aria-label={content.navPrimary}
        aria-hidden={!menuOpen}
      >
        <ul className="site-container site-mobile-nav-list">
          {navItems.map((item) => (
            <li key={item.href}>
              <a className="site-mobile-nav-link" href={item.href} onClick={closeMenu}>
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
