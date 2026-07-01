"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const INVENTORY_LINKS = [
  { href: "/inventory/products", label: "Products" },
  { href: "/inventory/orders/inbound", label: "Inbound" },
  { href: "/inventory/orders/outbound", label: "Outbound" },
  { href: "/inventory/orders", label: "Order history" },
] as const;

interface InventoryPageShellProps {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) {
    return false;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function InventoryPageShell({
  eyebrow,
  title,
  description,
  children,
}: InventoryPageShellProps): React.JSX.Element {
  const pathname = usePathname();

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">{eyebrow}</p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">{description}</p>
          <nav
            className="mt-4 flex flex-wrap gap-2"
            aria-label="Inventory section navigation"
          >
            {INVENTORY_LINKS.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "rounded-full border border-amber-300 bg-amber-300/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-amber-100"
                      : "rounded-full border border-amber-300/40 px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-amber-200/80 transition hover:border-amber-300/70 hover:bg-amber-300/10"
                  }
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </header>
        {children}
      </div>
    </main>
  );
}
