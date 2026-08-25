import type { ReactNode } from "react";

import { siteConfig } from "@/lib/site";
import { Navbar } from "./navbar";
import { Sidebar } from "./sidebar";
import { Footer } from "./footer";

export function AppShell({ children }: { children: ReactNode }) {
  const isSidebarArchetype =
    siteConfig.archetype === "dashboard" || siteConfig.archetype === "workflow";

  if (isSidebarArchetype) {
    return (
      <div className="d-flex min-vh-100">
        <Sidebar />
        <div className="d-flex flex-column flex-grow-1 min-vw-0">
          <header className="navbar navbar-expand bg-white border-bottom px-4 py-2 d-md-none">
            <span className="navbar-brand fw-bold text-dark mb-0 fs-6">{siteConfig.name}</span>
          </header>
          <main className="flex-grow-1 p-3 p-md-4 container-fluid">{children}</main>
          <Footer />
        </div>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column min-vh-100">
      <Navbar />
      <main className="flex-grow-1 container py-4">{children}</main>
      <Footer />
    </div>
  );
}
