'use client';

interface Props {
	progress: string | null;
}

export const ImplementationLiveProgress = ({ progress }: Props) => {
	const currentAction = progress || 'Preparando generación...';
	const isThinking = currentAction === 'Pensando' || currentAction.toLowerCase().startsWith('pensando');

	return (
		<div className='warning-popup'>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200 flex flex-col items-center gap-6 text-center'
				onClick={(e) => e.stopPropagation()}
			>
				<div>
					<h3 className='text-lg font-semibold text-neutral-800 mb-1.5'>
						Generando implementación
					</h3>
					<p className='text-sm text-neutral-500'>
						Transformando requisitos y modelo en código funcional.
					</p>
				</div>

				<div className='h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500 shrink-0' />

				{/* Línea fija única donde se actualizan los mensajes continuamente sin alterar el tamaño del modal */}
				<div className='h-7 w-full flex items-center justify-center px-2 overflow-hidden'>
					{isThinking ? (
						<span className='inline-flex items-center gap-2 text-sm font-semibold text-neutral-800 animate-fade-in'>
							<span className='h-1.5 w-1.5 rounded-full bg-ai-500 animate-pulse' />
							Pensando
						</span>
					) : (
						<span
							key={currentAction}
							className='text-sm font-medium text-neutral-700 truncate max-w-full'
							title={currentAction}
						>
							{currentAction}
						</span>
					)}
				</div>

				<span className='text-xs text-neutral-400'>
					Por favor, no cierres esta pestaña mientras finaliza la generación.
				</span>
			</div>
		</div>
	);
};
