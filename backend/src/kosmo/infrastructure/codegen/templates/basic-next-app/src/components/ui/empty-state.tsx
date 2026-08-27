import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "d-flex flex-column align-items-center justify-content-center text-center p-5 rounded border border-dashed bg-white",
        className,
      )}
    >
      {Icon ? (
        <div
          className="d-flex align-items-center justify-content-center rounded-circle bg-light mb-3 text-secondary"
          style={{ width: "3.5rem", height: "3.5rem" }}
        >
          <Icon size={24} />
        </div>
      ) : null}
      <h6 className="fw-semibold text-dark mb-1">{title}</h6>
      {description ? <p className="text-muted small mb-3">{description}</p> : null}
      {action}
    </div>
  );
}
