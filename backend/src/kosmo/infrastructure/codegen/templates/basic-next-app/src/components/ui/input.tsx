import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  isInvalid?: boolean;
}

export function Input({ className, isInvalid, ...props }: InputProps) {
  return (
    <input
      className={cn("form-control", isInvalid && "is-invalid", className)}
      {...props}
    />
  );
}
