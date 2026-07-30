import type { TranslationDictionary } from "@/lib/home-content";

interface ContactSectionProps {
  content: TranslationDictionary;
}

export function ContactSection({ content }: ContactSectionProps): React.JSX.Element {
  return (
    <section
      id="contact"
      className="section-compact"
      aria-labelledby="contact-heading"
    >
      <div className="grid gap-8 lg:grid-cols-[0.6fr_1.4fr] lg:items-end">
        <div>
          <p className="section-label">{content.contactEyebrow}</p>
          <h2 id="contact-heading" className="section-title brand-display uppercase">
            {content.contactTitle}
          </h2>
        </div>
        <address className="grid gap-3 not-italic sm:grid-cols-3">
          <a className="contact-card" href="mailto:hello@brasaland.com">
            <p className="contact-card-label">{content.contactEmailLabel}</p>
            <p className="contact-card-value">hello@brasaland.com</p>
          </a>
          <a className="contact-card" href="tel:+5741234567">
            <p className="contact-card-label">{content.contactColombiaLabel}</p>
            <p className="contact-card-value">+57 4 123 4567</p>
          </a>
          <a className="contact-card" href="tel:+13051234567">
            <p className="contact-card-label">{content.contactFloridaLabel}</p>
            <p className="contact-card-value">+1 305 123 4567</p>
          </a>
        </address>
      </div>
      <p className="order-notice mt-6 rounded-r-xl p-4 text-sm font-semibold sm:text-base">
        {content.orderNotice}
      </p>
    </section>
  );
}
