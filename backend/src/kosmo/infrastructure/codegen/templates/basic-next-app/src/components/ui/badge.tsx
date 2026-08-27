import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const toneClasses = {
  neutral: "bg-light text-dark border",
  success: "bg-success-subtle text-success-emphasis border border-success-subtle",
  warning: "bg-warning-subtle text-warning-emphasis border border-warning-subtle",
  danger: "bg-danger-subtle text-danger-emphasis border border-danger-subtle",
  primary: "bg-primary-subtle text-primary-emphasis border border-primary-subtle",
  info: "bg-info-subtle text-info-emphasis border border-info-subtle",
} as const;

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: keyof typeof toneClasses;
}

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "badge rounded-pill fw-medium d-inline-flex align-items-center gap-1",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
