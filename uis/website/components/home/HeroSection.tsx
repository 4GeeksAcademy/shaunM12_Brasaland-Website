import type { TranslationDictionary } from "@/lib/home-content";

interface HeroSectionProps {
  content: TranslationDictionary;
}

export function HeroSection({ content }: HeroSectionProps): React.JSX.Element {
  return (
    <section
      id="home"
      className="overflow-hidden rounded-3xl border border-amber-200/20 bg-gradient-to-br from-amber-300 via-amber-200 to-orange-200 p-6 text-stone-950 shadow-2xl shadow-black/20 sm:p-10"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-stone-700">{content.heroEyebrow}</p>
      <h1 className="brand-display mt-2 text-5xl uppercase leading-[0.95] tracking-wide sm:text-6xl lg:text-7xl">
        {content.heroTitle}
      </h1>
      <p className="mt-5 max-w-3xl text-lg leading-relaxed text-stone-800">{content.heroSubtitle}</p>
      <div className="mt-8 flex flex-wrap gap-3">
        <a
          href="/application.html"
          className="inline-flex items-center rounded-full bg-stone-950 px-6 py-3 text-base font-bold text-amber-200 transition hover:-translate-y-0.5 hover:bg-stone-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-950"
        >
          {content.heroCta}
        </a>
        <a
          href="#locations"
          className="inline-flex items-center rounded-full border border-stone-700 px-6 py-3 text-base font-bold text-stone-900 transition hover:bg-stone-100/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-900"
        >
          {content.heroSecondaryCta}
        </a>
      </div>
    </section>
  );
}
