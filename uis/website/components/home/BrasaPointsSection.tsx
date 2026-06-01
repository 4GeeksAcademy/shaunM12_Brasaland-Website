import type { TranslationDictionary } from "@/lib/home-content";

interface BrasaPointsSectionProps {
  content: TranslationDictionary;
}

export function BrasaPointsSection({ content }: BrasaPointsSectionProps): React.JSX.Element {
  return (
    <section
      id="brasa-points"
      className="mt-12 rounded-3xl border border-amber-200/20 bg-gradient-to-r from-orange-900/70 to-amber-800/60 p-6 sm:p-8"
      aria-labelledby="points-heading"
    >
      <h2 id="points-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-100">
        {content.pointsTitle}
      </h2>
      <p className="mt-2 text-lg font-semibold text-amber-100">{content.pointsSubtitle}</p>
      <ul className="mt-4 space-y-2 text-amber-50">
        <li>{content.pointsItem1}</li>
        <li>{content.pointsItem2}</li>
        <li>{content.pointsItem3}</li>
        <li>{content.pointsItem4}</li>
      </ul>
      <a
        href="/application.html"
        className="mt-6 inline-flex items-center rounded-full bg-amber-200 px-6 py-3 font-bold text-stone-950 transition hover:-translate-y-0.5 hover:bg-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-200"
      >
        {content.pointsCta}
      </a>
    </section>
  );
}
