import type { TranslationDictionary } from "@/lib/home-content";
import { getLocationsForCountry } from "@/lib/restaurant-locations";

interface LocationsSectionProps {
  content: TranslationDictionary;
}

export function LocationsSection({ content }: LocationsSectionProps): React.JSX.Element {
  const colombiaLocations = getLocationsForCountry("CO");
  const usaLocations = getLocationsForCountry("US");

  return (
    <section id="locations" className="section-compact" aria-labelledby="locations-heading">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="section-label">{content.locationsEyebrow}</p>
          <h2 id="locations-heading" className="section-title brand-display uppercase">
            {content.locationsTitle}
          </h2>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-[var(--text-muted)]">
          {content.locationsSummary}
        </p>
      </div>

      <div className="mt-9 grid gap-4 md:grid-cols-2">
        <article className="location-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="location-region">{content.colombiaTitle}</h3>
              <p className="location-region-meta">{content.locationsColombiaCount}</p>
            </div>
            <span className="location-count brand-display" aria-hidden="true">
              {colombiaLocations.length}
            </span>
          </div>
          <ul className="location-list space-y-3">
            {colombiaLocations.map((location) => (
              <li key={location.id} className="location-item">
                <span>
                  {location.name} — {location.city}
                </span>
              </li>
            ))}
          </ul>
          <p className="location-hours">{content.hoursLabel}</p>
        </article>

        <article className="location-card location-card-florida">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="location-region">{content.usaTitle}</h3>
              <p className="location-region-meta">{content.locationsUsaCount}</p>
            </div>
            <span className="location-count brand-display" aria-hidden="true">
              {usaLocations.length}
            </span>
          </div>
          <ul className="location-list space-y-3">
            {usaLocations.map((location) => (
              <li key={location.id} className="location-item">
                <span>
                  {location.name} — {location.city}
                </span>
              </li>
            ))}
          </ul>
          <p className="location-hours">{content.hoursLabel}</p>
        </article>
      </div>
    </section>
  );
}
