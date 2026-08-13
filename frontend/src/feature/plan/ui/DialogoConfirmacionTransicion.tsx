import type { TransitionDialogVariant } from '../types/plan';

interface DialogoConfirmacionTransicionProps {
	pendingCount: number;
	impactedPhases: string[];
	variant: TransitionDialogVariant;
	phaseName: string;
	onReview: () => void;
	onPostpone: () => void;
	onDiscard: () => void;
}

export const DialogoConfirmacionTransicion = ({
	pendingCount,
	impactedPhases,
	variant,
	phaseName,
	onReview,
	onPostpone,
	onDiscard,
}: DialogoConfirmacionTransicionProps) => {
	const isCurrentPhase = variant === 'currentPhase';

	const description = isCurrentPhase
		? `Tienes ${pendingCount} cambio(s) pendiente(s) en la fase actual (${phaseName}).`
		: `Tienes ${pendingCount} cambio(s) pendiente(s) que dejaste en la fase ${phaseName}.`;

	return (
		<div
			className='page-popup'
			onClick={onPostpone}
		>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-8 w-full max-w-lg mx-4 flex flex-col gap-5 border border-neutral-200'
				onClick={(e) => e.stopPropagation()}
			>
				<div className='text-center'>
					<div className='inline-flex items-center justify-center w-11 h-11 rounded-full bg-warning-50 mb-4'>
						<svg
							className='w-5 h-5 text-warning-700'
							fill='none'
							stroke='currentColor'
							viewBox='0 0 24 24'
							xmlns='http://www.w3.org/2000/svg'
						>
							<path
								strokeLinecap='round'
								strokeLinejoin='round'
								strokeWidth={2}
								d='M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
							/>
						</svg>
					</div>
					<h3 className='text-xl font-bold text-neutral-800 mb-2'>Cambios sin aplicar</h3>
					<p className='text-neutral-500 text-sm'>
						{description} ¿Qué deseas hacer antes de continuar?
					</p>
				</div>

				{impactedPhases.length > 0 && (
					<div className='bg-warning-50 border-l-4 border-warning-500 p-4 rounded-r-md'>
						<div className='flex gap-3'>
							<svg
								className='h-4 w-4 text-warning-500 shrink-0 mt-0.5'
								viewBox='0 0 20 20'
								fill='currentColor'
								aria-hidden='true'
							>
								<path
									fillRule='evenodd'
									d='M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z'
									clipRule='evenodd'
								/>
							</svg>
							<p className='text-xs text-warning-700'>
								El impacto de estos cambios afectará a:{' '}
								<strong className='font-semibold'>{impactedPhases.join(', ')}</strong>.
							</p>
						</div>
					</div>
				)}

				<div className='flex flex-col sm:flex-row justify-between gap-3 mt-2'>
					<button className='btn btn-destructive' onClick={onDiscard}>
						Descartar plan
					</button>
					<div className='flex flex-col sm:flex-row gap-3'>
						<button className='btn btn-secondary' onClick={onPostpone}>
							Dejar para después
						</button>
						<button className='btn btn-primary' onClick={onReview}>
							Revisar y aplicar
						</button>
					</div>
				</div>
			</div>
		</div>
	);
};
