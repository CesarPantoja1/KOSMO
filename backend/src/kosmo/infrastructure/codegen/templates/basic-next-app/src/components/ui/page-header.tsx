import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3 mb-4", className)}>
      <div>
        <h1 className="h3 fw-bold text-dark mb-1">{title}</h1>
        {description ? <p className="text-muted small mb-0">{description}</p> : null}
      </div>
      {actions ? <div className="d-flex align-items-center gap-2 flex-wrap">{actions}</div> : null}
    </div>
  );
}
