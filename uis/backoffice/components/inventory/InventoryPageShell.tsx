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
    <main className="bo-page">
      <div className="bo-container space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">{eyebrow}</p>
          <h1 className="bo-title">{title}</h1>
          <p className="bo-lead">{description}</p>
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
                  className={active ? "bo-subnav-link-active" : "bo-subnav-link"}
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
