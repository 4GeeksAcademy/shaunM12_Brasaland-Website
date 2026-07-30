import Image from "next/image";

import type { TranslationDictionary } from "@/lib/home-content";

interface HeroSectionProps {
  content: TranslationDictionary;
}

export function HeroSection({ content }: HeroSectionProps): React.JSX.Element {
  return (
    <section id="home" className="hero relative" aria-labelledby="hero-heading">
      <Image
        src="https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=1800&q=85"
        alt=""
        className="hero-media"
        fill
        priority
        sizes="(max-width: 1280px) 100vw, 1216px"
      />
      <div className="hero-shade" aria-hidden="true" />
      <div className="hero-content">
        <p className="eyebrow">{content.heroEyebrow}</p>
        <h1 id="hero-heading" className="hero-title brand-display uppercase">
          {content.heroTitle}
        </h1>
        <p className="hero-copy">{content.heroSubtitle}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href="/application.html" className="button-primary">
            {content.heroCta}
            <span aria-hidden="true">→</span>
          </a>
          <a href="#locations" className="button-secondary">
            {content.heroSecondaryCta}
          </a>
        </div>
      </div>
    </section>
  );
}
