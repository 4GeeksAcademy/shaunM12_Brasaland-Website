import type { TranslationDictionary } from "@/lib/home-content";

interface MenuSectionProps {
  content: TranslationDictionary;
}

export function MenuSection({ content }: MenuSectionProps): React.JSX.Element {
  return (
    <section
      id="menu"
      className="mt-12 rounded-3xl border border-amber-200/20 bg-stone-900/70 p-6 sm:p-8"
      aria-labelledby="menu-heading"
    >
      <h2 id="menu-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-300">
        {content.menuTitle}
      </h2>
      <p className="mt-4 max-w-3xl text-stone-200">{content.menuBody}</p>
    </section>
  );
}
