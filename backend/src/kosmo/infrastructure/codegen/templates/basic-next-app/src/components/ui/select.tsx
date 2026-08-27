import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  isInvalid?: boolean;
}

export function Select({ className, isInvalid, children, ...props }: SelectProps) {
  return (
    <select className={cn("form-select", isInvalid && "is-invalid", className)} {...props}>
      {children}
    </select>
  );
}
