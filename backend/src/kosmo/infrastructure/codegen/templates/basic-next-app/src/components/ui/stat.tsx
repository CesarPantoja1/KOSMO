import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface StatProps {
  title: string;
  value: string | number;
  description?: string;
  change?: string;
  isPositive?: boolean;
  icon?: LucideIcon;
  action?: ReactNode;
  className?: string;
}

export function Stat({
  title,
  value,
  description,
  change,
  isPositive,
  icon: Icon,
  action,
  className,
}: StatProps) {
  return (
    <div className={cn("card p-3 h-100", className)}>
      <div className="d-flex align-items-center justify-content-between mb-2">
        <span className="text-secondary small fw-medium text-uppercase">{title}</span>
        {Icon ? (
          <div
            className="d-flex align-items-center justify-content-center rounded bg-primary-subtle text-primary"
            style={{ width: "2.25rem", height: "2.25rem" }}
          >
            <Icon size={18} />
          </div>
        ) : null}
      </div>
      <div className="d-flex align-items-baseline gap-2 mb-1">
        <h3 className="h2 fw-bold text-dark mb-0">{value}</h3>
        {change ? (
          <span
            className={cn(
              "badge small",
              isPositive
                ? "bg-success-subtle text-success-emphasis"
                : "bg-danger-subtle text-danger-emphasis",
            )}
          >
            {change}
          </span>
        ) : null}
      </div>
      {description ? <p className="text-muted small mb-0 mt-1">{description}</p> : null}
      {action ? <div className="mt-3 pt-2 border-top">{action}</div> : null}
    </div>
  );
}
