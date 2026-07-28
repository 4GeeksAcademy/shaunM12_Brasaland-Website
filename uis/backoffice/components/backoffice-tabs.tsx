"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/context/AuthProvider";

interface BackofficeTab {
  href: string;
  label: string;
  adminOnly?: boolean;
}

const TABS: BackofficeTab[] = [
  { href: "/", label: "Candidate Tracker" },
  { href: "/data-processing", label: "Data Processing" },
  { href: "/registration-analytics", label: "Registration Analytics" },
  { href: "/incidents", label: "Incidents" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/inventory/products", label: "Inventory" },
  { href: "/reporting", label: "Reporting" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/account/profile", label: "Profile" },
  { href: "/account/users", label: "Users", adminOnly: true },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) {
    return false;
  }
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Horizontal tab bar to move between the main backoffice pages.
 * The "Users" tab only renders for admins, mirroring the session bar.
 */
export default function BackofficeTabs(): React.JSX.Element {
  const pathname = usePathname();
  const { user } = useAuth();

  const tabs = TABS.filter((tab) => !tab.adminOnly || user?.is_admin);

  return (
    <nav className="flex flex-wrap gap-2" aria-label="Backoffice navigation">
      {tabs.map((tab) => {
        const active = isActive(pathname, tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={
              active
                ? "rounded-full border border-[color:var(--bo-accent)] bg-[color:var(--bo-tab-active-bg)] px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--bo-accent)]"
                : "rounded-full border border-[color:var(--bo-tab-idle-border)] px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--bo-accent)]/80 transition hover:bg-[color:var(--bo-accent-soft)] hover:text-[color:var(--bo-accent)]"
            }
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
