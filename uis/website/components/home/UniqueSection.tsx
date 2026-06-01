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
    <section className="mt-12" aria-labelledby="unique-heading">
      <h2 id="unique-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-300">
        {content.uniqueTitle}
      </h2>
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <article key={card.title} className="rounded-2xl border border-amber-200/20 bg-stone-900/70 p-5">
            <h3 className="text-xl font-bold text-amber-200">{card.title}</h3>
            <ul className="mt-3 space-y-2 text-stone-200">
              <li>{card.points[0]}</li>
              <li>{card.points[1]}</li>
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
