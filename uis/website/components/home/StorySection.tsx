import Image from "next/image";
import type { TranslationDictionary } from "@/lib/home-content";

interface StorySectionProps {
  content: TranslationDictionary;
}

export function StorySection({ content }: StorySectionProps): React.JSX.Element {
  return (
    <section
      className="mt-12 grid gap-6 rounded-3xl border border-amber-200/20 bg-stone-900/80 p-6 sm:p-8 lg:grid-cols-2"
      aria-labelledby="story-heading"
    >
      <article>
        <h2 id="story-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-300">
          {content.storyTitle}
        </h2>
        <p className="mt-4 text-base leading-relaxed text-stone-200">{content.storyBody}</p>
      </article>
      <Image
        src="https://images.unsplash.com/photo-1529042410759-befb1204b468?auto=format&fit=crop&w=1600&q=80"
        alt="Latin-style parrilla spread with grilled meats, vegetables, and vibrant table styling"
        className="h-64 w-full rounded-2xl object-cover sm:h-80"
        loading="lazy"
        width={1200}
        height={800}
      />
    </section>
  );
}
