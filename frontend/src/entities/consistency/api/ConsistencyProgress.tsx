'use client';

interface PhaseState {
	phase: string;
	status: 'evaluating' | 'done' | 'error';
	message: string;
	affectedCount: number;
}

interface ConsistencyProgressProps {
	title: string;
	description: string;
	phases: PhaseState[];
	phaseLabels: Record<string, string>;
	isComplete: boolean;
}

export function ConsistencyProgress({
	title,
	description,
	phases,
	phaseLabels,
	isComplete,
}: ConsistencyProgressProps) {
	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/70'>
			<div className='w-full max-w-md rounded-xl bg-white p-8 shadow-2xl'>
				<h2 className='text-xl font-bold text-base-950 mb-2'>{title}</h2>
				<p className='text-sm text-base-600 mb-6'>{description}</p>

				<div className='space-y-3'>
					{phases.length === 0 && (
						<div className='flex items-center gap-3 text-sm text-base-500'>
							<div className='h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary-100 border-t-transparent' />
							<span>Preparando análisis...</span>
						</div>
					)}

					{phases.map((p) => (
						<div key={p.phase} className='flex items-center gap-3'>
							{p.status === 'evaluating' && (
								<div className='h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary-100 border-t-transparent' />
							)}
							{p.status === 'done' && (
								<span className='flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-status-success text-white text-xs font-bold'>
									✓
								</span>
							)}
							{p.status === 'error' && (
								<span className='flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-status-error text-white text-xs font-bold'>
									✗
								</span>
							)}
							<div className='flex-1'>
								<span className='text-sm font-medium text-base-800'>
									{phaseLabels[p.phase] || p.phase}
								</span>
								{p.status === 'done' && (
									<span className='ml-2 text-xs text-base-500'>
										{p.affectedCount > 0
											? `${p.affectedCount} impacto(s)`
											: 'Sin cambios'}
									</span>
								)}
							</div>
						</div>
					))}
				</div>

				{isComplete && phases.length > 0 && (
					<p className='mt-6 text-center text-sm text-base-500'>
						Análisis completado
					</p>
				)}
			</div>
		</div>
	);
}
