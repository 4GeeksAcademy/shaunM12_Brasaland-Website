import type { TranslationDictionary } from "@/lib/home-content";

interface LocationsSectionProps {
  content: TranslationDictionary;
}

export function LocationsSection({ content }: LocationsSectionProps): React.JSX.Element {
  return (
    <section id="locations" className="mt-12" aria-labelledby="locations-heading">
      <h2 id="locations-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-300">
        {content.locationsTitle}
      </h2>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-emerald-300/20 bg-emerald-900/30 p-5">
          <h3 className="text-xl font-bold text-emerald-200">{content.colombiaTitle}</h3>
          <ul className="mt-3 space-y-2 text-stone-200">
            <li>{content.colombiaPoint1}</li>
            <li>{content.hoursLabel}</li>
          </ul>
        </article>
        <article className="rounded-2xl border border-cyan-300/20 bg-cyan-900/30 p-5">
          <h3 className="text-xl font-bold text-cyan-200">{content.usaTitle}</h3>
          <ul className="mt-3 space-y-2 text-stone-200">
            <li>{content.usaPoint1}</li>
            <li>{content.hoursLabel}</li>
          </ul>
        </article>
      </div>
    </section>
  );
}
