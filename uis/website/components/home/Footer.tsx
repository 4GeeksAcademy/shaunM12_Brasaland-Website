import type { TranslationDictionary } from "@/lib/home-content";

interface FooterProps {
  content: TranslationDictionary;
}

export function Footer({ content }: FooterProps): React.JSX.Element {
  return (
    <footer className="site-footer">
      <div className="site-container flex flex-col gap-8 py-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <a className="brand-display text-4xl tracking-wide text-white" href="#home">
            Brasaland
          </a>
          <p className="mt-2 max-w-xs text-sm leading-relaxed">
            {content.brandTagline} · {content.footerTagline}
          </p>
          <p className="mt-5 text-xs">{content.footerCopyright}</p>
        </div>
        <nav aria-label={content.socialNav}>
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-white/40">
            {content.socialNav}
          </p>
          <ul className="flex gap-5 font-bold text-white/80">
            <li>
              <a
                className="footer-link"
                href="https://instagram.com/brasaland"
                target="_blank"
                rel="noopener noreferrer"
              >
                Instagram
              </a>
            </li>
            <li>
              <a
                className="footer-link"
                href="https://facebook.com/brasaland"
                target="_blank"
                rel="noopener noreferrer"
              >
                Facebook
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
