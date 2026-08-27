import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const variantClasses = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  outline: "btn-outline-primary",
  "outline-secondary": "btn-outline-secondary",
  ghost: "btn-link text-decoration-none",
  danger: "btn-danger",
  light: "btn-light border",
} as const;

const sizeClasses = {
  sm: "btn-sm",
  default: "",
  lg: "btn-lg",
} as const;

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variantClasses;
  size?: keyof typeof sizeClasses;
}

export function Button({
  className,
  variant = "primary",
  size = "default",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "btn d-inline-flex align-items-center justify-content-center gap-2",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
