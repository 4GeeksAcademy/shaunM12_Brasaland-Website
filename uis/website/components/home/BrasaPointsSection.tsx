import type { TranslationDictionary } from "@/lib/home-content";

interface BrasaPointsSectionProps {
  content: TranslationDictionary;
}

export function BrasaPointsSection({ content }: BrasaPointsSectionProps): React.JSX.Element {
  return (
    <section
      id="brasa-points"
      className="section"
      aria-labelledby="points-heading"
    >
      <div className="points-panel grid gap-10 px-6 py-10 sm:px-10 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16 lg:px-14 lg:py-14">
        <div className="flex flex-col items-start justify-center">
          <p className="section-label">{content.pointsEyebrow}</p>
          <h2 id="points-heading" className="section-title brand-display uppercase">
            {content.pointsTitle}
          </h2>
          <p className="mt-4 text-xl font-bold text-[var(--text)]">
            {content.pointsSubtitle}
          </p>
          <a href="/application.html" className="button-primary mt-7">
            {content.pointsCta}
            <span aria-hidden="true">→</span>
          </a>
        </div>

        <ol className="grid content-center gap-5 sm:grid-cols-2">
          <li className="points-item">{content.pointsItem1}</li>
          <li className="points-item">{content.pointsItem2}</li>
          <li className="points-item">{content.pointsItem3}</li>
          <li className="points-item">{content.pointsItem4}</li>
        </ol>
      </div>
    </section>
  );
}
