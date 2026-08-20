import type { PhaseConsistencyStatus } from '@/entities/consistency';

interface PhaseStatusBadgeProps {
	status: PhaseConsistencyStatus | undefined;
	isLoading?: boolean;
}

export function PhaseStatusBadge({ status, isLoading }: PhaseStatusBadgeProps) {
	if (!status && isLoading) {
		return (
			<span
				className='flex h-4 min-w-4 items-center justify-center rounded-full bg-warning-500 px-1'
				title='Cargando consistencia…'
			>
				<svg
					className='h-2.5 w-2.5 animate-spin text-neutral-0'
					viewBox='0 0 24 24'
					fill='none'
				>
					<circle
						className='opacity-25'
						cx='12'
						cy='12'
						r='10'
						stroke='currentColor'
						strokeWidth='4'
					/>
					<path
						className='opacity-75'
						fill='currentColor'
						d='M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z'
					/>
				</svg>
			</span>
		);
	}

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
				className='flex h-4 min-w-4 items-center justify-center rounded-full bg-warning-500 px-1 text-[10px] font-semibold text-neutral-0'
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
