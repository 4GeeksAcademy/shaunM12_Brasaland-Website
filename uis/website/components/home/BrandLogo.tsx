interface BrandLogoProps {
  tagline: string;
}

export function BrandLogo({ tagline }: BrandLogoProps): React.JSX.Element {
  return (
    <div className="flex items-center gap-3" aria-label="Brasaland logo">
      <svg
        viewBox="0 0 88 88"
        className="h-12 w-12 shrink-0"
        role="img"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="logoFlameGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fcd34d" />
            <stop offset="55%" stopColor="#fb923c" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>

        <rect x="4" y="4" width="80" height="80" rx="20" fill="#17120e" stroke="#fcd34d" strokeOpacity="0.38" strokeWidth="2" />

        <circle cx="44" cy="44" r="22" fill="none" stroke="#fcd34d" strokeOpacity="0.8" strokeWidth="2" />

        <path
          d="M44 20 C50 28, 50 36, 44 42 C38 36, 38 28, 44 20 Z"
          fill="url(#logoFlameGradient)"
        />
        <path
          d="M44 27 C47 31, 47 35, 44 38 C41 35, 41 31, 44 27 Z"
          fill="#fff7d1"
          fillOpacity="0.7"
        />

        <path d="M28 48 H60" stroke="#fcd34d" strokeOpacity="0.7" strokeWidth="2" strokeLinecap="round" />
        <path d="M31 54 H57" stroke="#fcd34d" strokeOpacity="0.7" strokeWidth="2" strokeLinecap="round" />
        <path d="M34 60 H54" stroke="#fcd34d" strokeOpacity="0.7" strokeWidth="2" strokeLinecap="round" />
      </svg>

      <div>
        <p className="brand-display text-3xl leading-none tracking-wide text-amber-300 sm:text-4xl">
          Brasaland
        </p>
        <p className="text-xs uppercase tracking-[0.2em] text-stone-300">{tagline}</p>
      </div>
    </div>
  );
}
