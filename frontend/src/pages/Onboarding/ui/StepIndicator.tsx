'use client';

import { Check } from '@/shared/ui';

interface StepIndicatorProps {
	currentStep: number;
	totalSteps: number;
	steps: Array<{ label: string; completed: boolean }>;
}

export function StepIndicator({ currentStep, totalSteps, steps }: StepIndicatorProps) {
	return (
		<div className='flex items-center gap-1.5'>
			{steps.map((step, index) => {
				const isActive = index === currentStep;
				const isCompleted = step.completed;

				return (
					<div key={step.label} className='flex items-center gap-1.5'>
						<div className='flex items-center gap-2'>
							<div
								className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-all duration-200 ${
									isCompleted
										? 'bg-wizard-completed text-neutral-0 shadow-sm'
										: isActive
											? 'bg-wizard-active text-neutral-0 shadow-sm ring-2 ring-wizard-active-ring'
											: 'bg-wizard-pending-light text-wizard-pending border border-wizard-pending'
								}`}
							>
								{isCompleted ? <Check size={14} color='text-neutral-0' /> : index + 1}
							</div>
							<span
								className={`text-sm font-medium hidden sm:inline transition-colors ${
									isActive
										? 'text-wizard-label-active'
										: isCompleted
											? 'text-wizard-label-completed'
											: 'text-wizard-label-pending'
								}`}
							>
								{step.label}
							</span>
						</div>
						{index < totalSteps - 1 && (
							<div
								className={`w-8 h-0.5 rounded-full transition-colors ${
									isCompleted
										? 'bg-wizard-connector-done'
										: 'bg-wizard-connector-pending'
								}`}
							/>
						)}
					</div>
				);
			})}
		</div>
	);
}
