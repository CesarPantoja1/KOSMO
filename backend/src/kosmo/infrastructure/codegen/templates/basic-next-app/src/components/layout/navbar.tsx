"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { features } from "@/lib/feature-registry";
import { siteConfig } from "@/lib/site";
import { cn } from "@/lib/utils";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
        <Link href="/" className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm font-semibold text-neutral-900">
            {siteConfig.name}
          </span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto" aria-label="Navegación principal">
          {features.map((feature) => {
            const active = pathname === feature.route;
            return (
              <Link
                key={feature.slug}
                href={feature.route}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors",
                  active
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
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
