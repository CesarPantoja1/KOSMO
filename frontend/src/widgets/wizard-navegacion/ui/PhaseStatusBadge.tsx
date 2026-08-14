import type { PhaseConsistencyStatus } from '@/entities/consistency';

interface PhaseStatusBadgeProps {
	status: PhaseConsistencyStatus | undefined;
}

export function PhaseStatusBadge({ status }: PhaseStatusBadgeProps) {
	if (!status) return null;

	if (status.evaluating > 0) {
		return (
			<span
				className='flex h-4 w-4 items-center justify-center rounded-full bg-warning-500'
				title={`Evaluando consistencia (${status.evaluating})`}
			>
				<span className='h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-0' />
			</span>
		);
	}

	if (status.pending > 0) {
		return (
			<span
				className='flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-500 px-1 text-[10px] font-semibold text-neutral-0'
				title={`${status.pending} cambio(s) pendiente(s) de revisión`}
			>
				{status.pending}
			</span>
		);
	}

	if (status.failed > 0) {
		return (
			<span
				className='flex h-4 w-4 items-center justify-center rounded-full bg-error-500'
				title={`Fallos en la evaluación (${status.failed})`}
			>
				<span className='text-[10px] font-bold text-neutral-0'>!</span>
			</span>
		);
	}

	return null;
}
