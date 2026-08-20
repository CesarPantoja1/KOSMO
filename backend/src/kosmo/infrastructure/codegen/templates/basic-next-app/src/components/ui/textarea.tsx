import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900",
        "placeholder:text-neutral-400 focus:border-indigo-500 focus:outline-2 focus:outline-indigo-600",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
