import type { SupportedLanguage } from "@/lib/home-content";
import {
  brasalandMenu,
  getMenuPrice,
  type MenuLocaleContent,
} from "@/lib/brasaland-menu";

interface MenuCatalogProps {
  language: SupportedLanguage;
}

export function MenuCatalog({ language }: MenuCatalogProps): React.JSX.Element {
  const menu: MenuLocaleContent = brasalandMenu[language];

  return (
    <div className="menu-catalog">
      <header className="menu-page-hero">
        <p className="section-label">{menu.hero.eyebrow}</p>
        <h1 className="menu-page-title brand-display uppercase">{menu.hero.title}</h1>
        <p className="menu-page-description">{menu.hero.description}</p>
        <ul className="menu-page-badges">
          {menu.hero.badges.map((badge) => (
            <li key={badge} className="menu-page-badge">
              {badge}
            </li>
          ))}
        </ul>
      </header>

      <nav className="menu-category-nav" aria-label={language === "en" ? "Menu categories" : "Categorias del menu"}>
        <ul className="menu-category-nav-list">
          {menu.sections.map((section) => (
            <li key={section.id}>
              <a className="menu-category-pill" href={`#${section.id}`}>
                {section.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="menu-sections">
        {menu.sections.map((section) => (
          <section
            key={section.id}
            id={section.id}
            className="menu-section-block"
            aria-labelledby={`${section.id}-heading`}
          >
            <h2 id={`${section.id}-heading`} className="menu-section-title brand-display uppercase">
              {section.title}
            </h2>
            <ul className="menu-item-list">
              {section.items.map((item) => (
                <li key={item.name} className="menu-item-row">
                  <div className="menu-item-copy">
                    <h3 className="menu-item-name">{item.name}</h3>
                    <p className="menu-item-description">{item.description}</p>
                  </div>
                  <p className="menu-item-price">{getMenuPrice(item, language)}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
