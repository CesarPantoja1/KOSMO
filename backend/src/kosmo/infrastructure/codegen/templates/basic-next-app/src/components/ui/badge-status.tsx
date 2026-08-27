import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export type StatusType =
  | "pending"
  | "in_progress"
  | "completed"
  | "active"
  | "inactive"
  | "rejected"
  | "draft";

export interface BadgeStatusProps extends HTMLAttributes<HTMLSpanElement> {
  status: StatusType | string;
  label?: string;
}

const statusConfig: Record<
  string,
  { label: string; bg: string; dot: string }
> = {
  pending: {
    label: "Pendiente",
    bg: "bg-warning-subtle text-warning-emphasis border border-warning-subtle",
    dot: "bg-warning",
  },
  in_progress: {
    label: "En Progreso",
    bg: "bg-info-subtle text-info-emphasis border border-info-subtle",
    dot: "bg-info",
  },
  completed: {
    label: "Completado",
    bg: "bg-success-subtle text-success-emphasis border border-success-subtle",
    dot: "bg-success",
  },
  active: {
    label: "Activo",
    bg: "bg-success-subtle text-success-emphasis border border-success-subtle",
    dot: "bg-success",
  },
  inactive: {
    label: "Inactivo",
    bg: "bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle",
    dot: "bg-secondary",
  },
  rejected: {
    label: "Rechazado",
    bg: "bg-danger-subtle text-danger-emphasis border border-danger-subtle",
    dot: "bg-danger",
  },
  draft: {
    label: "Borrador",
    bg: "bg-light text-secondary border",
    dot: "bg-secondary",
  },
};

export function BadgeStatus({
  status,
  label,
  className,
  ...props
}: BadgeStatusProps) {
  const config = statusConfig[status] || {
    label: status,
    bg: "bg-light text-secondary border",
    dot: "bg-secondary",
  };

  return (
    <span
      className={cn(
        "badge rounded-pill fw-medium d-inline-flex align-items-center gap-2 px-2.5 py-1",
        config.bg,
        className,
      )}
      {...props}
    >
      <span
        className={cn("rounded-circle", config.dot)}
        style={{ width: "0.5rem", height: "0.5rem" }}
      />
      <span>{label ?? config.label}</span>
    </span>
  );
}
