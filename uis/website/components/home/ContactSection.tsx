import type { TranslationDictionary } from "@/lib/home-content";

interface ContactSectionProps {
  content: TranslationDictionary;
}

export function ContactSection({ content }: ContactSectionProps): React.JSX.Element {
  return (
    <section
      id="contact"
      className="mt-12 rounded-3xl border border-amber-200/20 bg-stone-900/80 p-6 sm:p-8"
      aria-labelledby="contact-heading"
    >
      <h2 id="contact-heading" className="brand-display text-4xl uppercase tracking-wide text-amber-300">
        {content.contactTitle}
      </h2>
      <ul className="mt-4 space-y-2 text-stone-200">
        <li>
          <span className="font-semibold text-stone-50">{content.contactEmailLabel}</span> hello@brasaland.com
        </li>
        <li>
          <span className="font-semibold text-stone-50">{content.contactColombiaLabel}</span> +57 4 123 4567
        </li>
        <li>
          <span className="font-semibold text-stone-50">{content.contactFloridaLabel}</span> +1 305 123 4567
        </li>
      </ul>
      <p className="mt-5 rounded-xl border border-amber-200/30 bg-amber-100/10 p-4 text-sm font-semibold text-amber-100 sm:text-base">
        {content.orderNotice}
      </p>
    </section>
  );
}
