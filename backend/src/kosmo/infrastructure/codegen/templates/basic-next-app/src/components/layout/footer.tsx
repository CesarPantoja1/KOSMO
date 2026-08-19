import { siteConfig } from "@/lib/site";

export function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 sm:flex-row">
        <p className="text-xs text-neutral-500">{siteConfig.name}</p>
        <p className="text-xs text-neutral-400">Generado con KOSMO</p>
      </div>
    </footer>
  );
}
