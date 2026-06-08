import type { TranslationDictionary } from "@/lib/home-content";

interface FooterProps {
  content: TranslationDictionary;
}

export function Footer({ content }: FooterProps): React.JSX.Element {
  return (
    <footer className="border-t border-amber-200/10 bg-stone-950/95">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-6 text-sm text-stone-300 sm:px-6 sm:text-base lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <p>{content.footerCopyright}</p>
        <nav aria-label={content.socialNav}>
          <ul className="flex gap-4">
            <li>
              <a
                className="hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
                href="https://instagram.com/brasaland"
                target="_blank"
                rel="noopener noreferrer"
              >
                Instagram
              </a>
            </li>
            <li>
              <a
                className="hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
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
