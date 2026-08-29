import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";

/**
 * Contrato de una feature implementada.
 *
 * Cada feature vive en `src/features/<slug>/` como un slice autocontenido:
 * `manifest.ts`, `logic.ts`, `components/` y su ruta en `src/app/<slug>/page.tsx`.
 *
 * Eliminar una feature es tan simple como borrar su slice y quitar su import
 * del registro de navegación: el shell y el resto de features no dependen de ella.
 */
export interface FeatureManifest {
  slug: string;
  title: string;
  description: string;
  route: string;
  icon?: LucideIcon | ComponentType<{ size?: number; className?: string }>;
}
