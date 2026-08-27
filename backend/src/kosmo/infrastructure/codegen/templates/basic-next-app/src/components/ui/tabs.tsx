import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  badge?: string | number;
  icon?: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  variant?: "tabs" | "pills";
  className?: string;
}

export function Tabs({
  items,
  activeId,
  onChange,
  variant = "tabs",
  className,
}: TabsProps) {
  return (
    <ul className={cn("nav", variant === "pills" ? "nav-pills" : "nav-tabs", className)}>
      {items.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <li key={tab.id} className="nav-item">
            <button
              type="button"
              onClick={() => onChange(tab.id)}
              className={cn(
                "nav-link d-flex align-items-center gap-2",
                isActive ? "active" : "text-secondary",
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.badge !== undefined ? (
                <span
                  className={cn(
                    "badge rounded-pill small",
                    isActive ? "bg-primary text-white" : "bg-secondary-subtle text-secondary",
                  )}
                >
                  {tab.badge}
                </span>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
