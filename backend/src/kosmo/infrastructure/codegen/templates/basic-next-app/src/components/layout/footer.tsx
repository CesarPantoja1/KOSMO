import { siteConfig } from "@/lib/site";

export function Footer() {
  return (
    <footer className="border-top bg-white py-3 mt-auto">
      <div className="container-fluid d-flex flex-column flex-sm-row align-items-center justify-content-between gap-2 px-4">
        <p className="small text-secondary mb-0">{siteConfig.name}</p>
        <p className="small text-muted mb-0">Generado con KOSMO</p>
      </div>
    </footer>
  );
}
