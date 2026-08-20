'use client';

interface Props {
	progress: string | null;
	currentThought: string | null;
}

export const ImplementationLiveProgress = ({ progress, currentThought }: Props) => {
	const currentAction = progress || 'Preparando generación...';

	return (
		<div className='warning-popup'>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200 flex flex-col items-center gap-5 text-center'
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

				<div className='h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />

				<div className='flex flex-col items-center gap-3 w-full'>
					<span className='text-sm font-medium text-neutral-700 px-2 min-h-[1.25rem] transition-all'>
						{currentAction}
					</span>

					{currentThought && (
						<div className='w-full rounded-lg bg-ai-50/70 border border-ai-100 p-3 text-xs text-ai-900 leading-relaxed text-left max-h-24 overflow-y-auto'>
							<div className='flex items-center gap-1.5 font-semibold text-ai-700 mb-1'>
								<span className='h-1.5 w-1.5 rounded-full bg-ai-500 animate-pulse' />
								<span>Pensamiento:</span>
							</div>
							<p className='font-mono text-[11px] text-neutral-700 whitespace-pre-wrap'>
								{currentThought}
							</p>
						</div>
					)}
				</div>

				<span className='text-xs text-neutral-400'>
					Por favor, no cierres esta pestaña mientras finaliza la generación.
				</span>
			</div>
		</div>
	);
};
