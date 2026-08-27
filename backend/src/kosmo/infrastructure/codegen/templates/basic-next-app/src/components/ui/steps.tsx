import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export interface StepItem {
  id: string | number;
  title: string;
  description?: string;
}

export interface StepsProps {
  steps: StepItem[];
  currentStep: number;
  className?: string;
}

export function Steps({ steps, currentStep, className }: StepsProps) {
  return (
    <div className={cn("d-flex align-items-center justify-content-between w-100 py-3", className)}>
      {steps.map((step, index) => {
        const stepNumber = index + 1;
        const isCompleted = stepNumber < currentStep;
        const isCurrent = stepNumber === currentStep;

        return (
          <div key={step.id} className="d-flex align-items-center flex-grow-1">
            <div className="d-flex align-items-center gap-2">
              <div
                className={cn(
                  "rounded-circle d-flex align-items-center justify-content-center fw-bold small",
                  isCompleted && "bg-success text-white",
                  isCurrent && "bg-primary text-white shadow-sm",
                  !isCompleted && !isCurrent && "bg-light text-secondary border",
                )}
                style={{ width: "2rem", height: "2rem" }}
              >
                {isCompleted ? <Check size={14} /> : stepNumber}
              </div>
              <div className="d-none d-sm-block">
                <p
                  className={cn(
                    "mb-0 small fw-medium",
                    isCurrent ? "text-dark" : "text-secondary",
                  )}
                >
                  {step.title}
                </p>
                {step.description ? (
                  <p className="mb-0 text-muted" style={{ fontSize: "0.75rem" }}>
                    {step.description}
                  </p>
                ) : null}
              </div>
            </div>
            {index < steps.length - 1 ? (
              <div
                className={cn(
                  "flex-grow-1 mx-3 border-top",
                  isCompleted ? "border-success" : "border-secondary-subtle",
                )}
                style={{ height: "1px" }}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
