"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { features } from "@/lib/feature-registry";
import { siteConfig } from "@/lib/site";
import { cn } from "@/lib/utils";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="navbar navbar-expand-lg bg-white border-bottom sticky-top py-2 px-3 shadow-sm">
      <div className="container-fluid">
        <Link href="/" className="navbar-brand fw-bold text-dark text-truncate me-4">
          {siteConfig.name}
        </Link>
        <nav className="navbar-nav me-auto d-flex flex-row gap-2 overflow-auto" aria-label="Navegación principal">
          <Link
            href="/"
            aria-current={pathname === "/" ? "page" : undefined}
            className={cn(
              "nav-link px-3 py-1.5 rounded text-nowrap",
              pathname === "/" ? "active fw-semibold bg-light text-primary" : "text-secondary",
            )}
          >
            Inicio
          </Link>
          {features.map((feature) => {
            const active = pathname === feature.route;
            return (
              <Link
                key={feature.slug}
                href={feature.route}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "nav-link px-3 py-1.5 rounded text-nowrap",
                  active ? "active fw-semibold bg-light text-primary" : "text-secondary",
                )}
              >
                {feature.title}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

