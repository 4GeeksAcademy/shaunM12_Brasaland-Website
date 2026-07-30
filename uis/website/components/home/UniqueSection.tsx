import type { TranslationDictionary } from "@/lib/home-content";

interface FeatureCard {
  title: string;
  points: [string, string];
}

interface UniqueSectionProps {
  content: TranslationDictionary;
}

export function UniqueSection({ content }: UniqueSectionProps): React.JSX.Element {
  const cards: FeatureCard[] = [
    {
      title: content.qualityTitle,
      points: [content.qualityPoint1, content.qualityPoint2],
    },
    {
      title: content.experienceTitle,
      points: [content.experiencePoint1, content.experiencePoint2],
    },
    {
      title: content.speedTitle,
      points: [content.speedPoint1, content.speedPoint2],
    },
  ];

  return (
    <section className="section-compact" aria-labelledby="unique-heading">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="section-label">{content.uniqueEyebrow}</p>
          <h2 id="unique-heading" className="section-title brand-display uppercase">
            {content.uniqueTitle}
          </h2>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-[var(--text-muted)]">
          {content.uniqueSummary}
        </p>
      </div>
      <div className="mt-9 grid gap-4 md:grid-cols-3">
        {cards.map((card, index) => (
          <article key={card.title} className="feature-card">
            <span className="feature-number">0{index + 1}</span>
            <h3 className="feature-title">{card.title}</h3>
            <ul className="mt-4 space-y-3">
              <li className="feature-point">{card.points[0]}</li>
              <li className="feature-point">{card.points[1]}</li>
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
