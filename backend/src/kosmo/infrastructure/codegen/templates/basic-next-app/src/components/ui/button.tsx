import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const variantClasses = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700 focus-visible:ring-indigo-600",
  secondary: "bg-white text-neutral-900 border border-neutral-300 hover:bg-neutral-100",
  outline: "bg-transparent text-indigo-700 border border-indigo-300 hover:bg-indigo-50",
  ghost: "bg-transparent text-neutral-700 hover:bg-neutral-100",
  danger: "bg-red-600 text-white hover:bg-red-700",
} as const;

const sizeClasses = {
  sm: "h-8 px-3 text-xs",
  default: "h-10 px-4 text-sm",
  lg: "h-11 px-6 text-base",
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
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
