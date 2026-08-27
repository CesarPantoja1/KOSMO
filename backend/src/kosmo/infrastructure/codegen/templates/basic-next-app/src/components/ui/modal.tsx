"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";

import { cn } from "@/lib/utils";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "default" | "lg" | "xl";
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = "default",
  className,
}: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.classList.add("modal-open");
    } else {
      document.body.classList.remove("modal-open");
    }
    return () => {
      document.body.classList.remove("modal-open");
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const sizeClass = {
    sm: "modal-sm",
    default: "",
    lg: "modal-lg",
    xl: "modal-xl",
  }[size];

  return (
    <>
      <div
        className="modal fade show d-block"
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        style={{ backgroundColor: "rgba(15, 23, 42, 0.5)", zIndex: 1055 }}
      >
        <div className={cn("modal-dialog modal-dialog-centered", sizeClass, className)}>
          <div className="modal-content shadow border-0">
            <div className="modal-header border-bottom py-3 px-4">
              <h5 className="modal-title h5 fw-semibold text-dark mb-0">{title}</h5>
              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={onClose}
              />
            </div>
            <div className="modal-body p-4">{children}</div>
            {footer ? (
              <div className="modal-footer border-top bg-light py-2 px-4">{footer}</div>
            ) : null}
          </div>
        </div>
      </div>
    </>
  );
}
