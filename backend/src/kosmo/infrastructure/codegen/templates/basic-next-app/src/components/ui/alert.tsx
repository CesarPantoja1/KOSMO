import type { ReactNode } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

import { cn } from "@/lib/utils";

export interface AlertProps {
  variant?: "info" | "success" | "warning" | "danger";
  title?: string;
  children: ReactNode;
  icon?: boolean;
  onClose?: () => void;
  className?: string;
}

const icons = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
};

export function Alert({
  variant = "info",
  title,
  children,
  icon = true,
  onClose,
  className,
}: AlertProps) {
  const IconComponent = icons[variant];

  return (
    <div
      className={cn(
        "alert d-flex align-items-start gap-3",
        `alert-${variant}`,
        onClose && "alert-dismissible",
        className,
      )}
      role="alert"
    >
      {icon && IconComponent ? (
        <div className="shrink-0 mt-1">
          <IconComponent size={18} />
        </div>
      ) : null}
      <div className="flex-grow-1">
        {title ? <h6 className="alert-heading fw-semibold mb-1">{title}</h6> : null}
        <div className="small">{children}</div>
      </div>
      {onClose ? (
        <button
          type="button"
          className="btn-close"
          aria-label="Cerrar"
          onClick={onClose}
        />
      ) : null}
    </div>
  );
}
