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

function ConsistencyProgress({
	title,
	description,
	phases,
	phaseLabels,
	isComplete,
}: ConsistencyProgressProps) {
	return (
		<div className='warning-popup'>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200'
				onClick={(e) => e.stopPropagation()}
			>
				<h3 className='text-lg font-semibold text-neutral-800 mb-2 text-center'>{title}</h3>
				<p className='text-sm text-neutral-500 text-center mb-6'>{description}</p>

				<div className='space-y-3'>
					{phases.length === 0 && (
						<div className='flex items-center gap-3 text-sm text-neutral-500'>
							<div className='h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />
							<span>Conectando con el motor de análisis...</span>
						</div>
					)}

					{phases.map((p) => (
						<div key={p.phase} className='flex items-center gap-3'>
							{p.status === 'evaluating' && (
								<div className='h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />
							)}
							{p.status === 'done' && (
								<span className='flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success-500 text-white text-xs font-bold'>
									✓
								</span>
							)}
							{p.status === 'error' && (
								<span className='flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-error-500 text-white text-xs font-bold'>
									✗
								</span>
							)}
							<div className='flex-1'>
								<span className='text-sm font-medium text-neutral-800'>
									{phaseLabels[p.phase] || p.phase}
								</span>
								{p.status === 'done' && (
									<span className='ml-2 text-xs text-neutral-500'>
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
					<p className='mt-6 text-center text-sm text-neutral-400'>Análisis completado</p>
				)}
			</div>
		</div>
	);
}

export { ConsistencyProgress };
