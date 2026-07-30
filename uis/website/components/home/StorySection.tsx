import Image from "next/image";
import type { TranslationDictionary } from "@/lib/home-content";

interface StorySectionProps {
  content: TranslationDictionary;
}

export function StorySection({ content }: StorySectionProps): React.JSX.Element {
  return (
    <section
      className="section grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16"
      aria-labelledby="story-heading"
    >
      <article className="lg:pr-4">
        <p className="section-label">{content.storyEyebrow}</p>
        <h2 id="story-heading" className="section-title brand-display uppercase">
          {content.storyTitle}
        </h2>
        <p className="section-copy mt-6">{content.storyBody}</p>
        <div className="mt-8 flex items-center gap-4 border-t border-[var(--border)] pt-6">
          <span className="brand-display text-5xl leading-none text-[var(--brand-yellow-strong)]">
            18
          </span>
          <p className="max-w-44 text-sm font-bold uppercase leading-snug tracking-[0.12em] text-[var(--text-muted)]">
            {content.storyYears}
          </p>
        </div>
      </article>

      <div className="story-image relative">
        <Image
          src="https://images.unsplash.com/photo-1529042410759-befb1204b468?auto=format&fit=crop&w=1600&q=80"
          alt="Latin-style parrilla spread with grilled meats, vegetables, and vibrant table styling"
          className="h-full w-full object-cover"
          loading="lazy"
          fill
          sizes="(max-width: 1024px) 100vw, 55vw"
        />
        <div className="story-stat">
          <span className="brand-display text-4xl leading-none text-[var(--brand-yellow)]">
            14
          </span>
          <p className="mt-1 text-xs font-bold uppercase tracking-[0.14em] text-white/70">
            {content.storyLocations}
          </p>
        </div>
      </div>
    </section>
  );
}
