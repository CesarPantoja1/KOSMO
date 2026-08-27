import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  isInvalid?: boolean;
}

export function Textarea({ className, isInvalid, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn("form-control", isInvalid && "is-invalid", className)}
      rows={props.rows ?? 3}
      {...props}
    />
  );
}
