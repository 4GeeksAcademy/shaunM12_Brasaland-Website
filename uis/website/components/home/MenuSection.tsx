import type { TranslationDictionary } from "@/lib/home-content";

interface MenuSectionProps {
  content: TranslationDictionary;
}

export function MenuSection({ content }: MenuSectionProps): React.JSX.Element {
  return (
    <section
      id="menu"
      className="menu-panel"
      aria-labelledby="menu-heading"
    >
      <div className="menu-accent" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="relative grid gap-10 px-6 py-12 sm:px-10 lg:grid-cols-[1fr_0.8fr] lg:px-14 lg:py-16">
        <div>
          <p className="eyebrow">{content.menuEyebrow}</p>
          <h2
            id="menu-heading"
            className="brand-display mt-3 text-5xl uppercase leading-none tracking-wide text-white sm:text-6xl"
          >
            {content.menuTitle}
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-white/65">
            {content.menuBody}
          </p>
          <p className="mt-3 text-sm font-semibold uppercase tracking-[0.12em] text-white/50">
            {content.menuTeaserLine}
          </p>
          <a href="/menu" className="button-primary mt-7 inline-flex">
            {content.menuCta}
            <span aria-hidden="true">→</span>
          </a>
        </div>

        <div className="grid grid-cols-2 gap-3 self-end">
          {[
            content.menuValue1,
            content.menuValue2,
            content.menuValue3,
            content.menuValue4,
          ].map((label, index) => (
            <div
              key={label}
              className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
            >
              <span className="brand-display text-3xl text-[var(--brand-yellow)]">
                0{index + 1}
              </span>
              <p className="mt-2 text-xs font-bold uppercase tracking-[0.15em] text-white/60">
                {label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
