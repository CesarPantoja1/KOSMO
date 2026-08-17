'use client';

import { Ai, Close, Loading } from '@/shared/ui';
import type { SuggestCharacteristic } from '@/entities/characteristic';
import { useCharacteristicModal } from '../hooks/use-characteristic-modal';

type Props = {
	onClose: () => void;
	onApply: (selected: SuggestCharacteristic) => void;
};

const CharacteristicModal = ({ onClose, onApply }: Props) => {
	const { alternatives, selectedId, isLoading, hasError, handleCardClick, handleApply } =
		useCharacteristicModal(onApply);

	return (
		<>
			{isLoading ? (
				<Loading
					title='Buscando ideas'
					description='El asistente está generando sugerencias de funcionalidades para tu proyecto...'
				/>
			) : (
				<div
					className='fixed inset-0 z-50 flex items-center justify-center bg-black/40'
					onClick={onClose}
				>
					{hasError && <ErrorState />}

					{!isLoading && !hasError && (
						<div
							className='bg-neutral-0 w-full max-w-xl p-7 rounded-xl border border-neutral-200 shadow-lg flex flex-col items-center gap-5'
							onClick={(e) => e.stopPropagation()}
						>
							<div className='w-full flex flex-col gap-3'>
								<div className='flex items-start justify-between gap-3'>
									<h2 className='text-xl font-bold text-neutral-800'>
										Ideas de funcionalidades
									</h2>
									<button
										className='cursor-pointer text-neutral-400 hover:text-neutral-700 transition-colors shrink-0'
										onClick={onClose}
									>
										<Close color='text-current' size={20} />
									</button>
								</div>
								<p className='text-sm text-neutral-500'>
									Sugerencias generadas por IA basadas en el contexto de tu proyecto.
									Selecciona una para usarla como base.
								</p>
							</div>

							<div className='w-full flex flex-col gap-3'>
								{alternatives.map((alt) => {
									const isSelected = selectedId === alt.number;
									return (
										<button
											key={alt.number}
											onClick={() => handleCardClick(alt.number)}
											className={`w-full p-4 flex flex-col items-start gap-2 cursor-pointer rounded-lg text-left transition-all duration-150 ${
												isSelected
													? 'border-2 border-primary-500 bg-primary-50 shadow-sm'
													: 'border border-neutral-200 bg-neutral-50 hover:border-neutral-300 hover:shadow-sm'
											}`}
										>
											<h3
												className={`text-sm font-semibold ${
													isSelected ? 'text-primary-600' : 'text-neutral-800'
												}`}
											>
												{alt.title}
											</h3>
											<p className='text-xs text-neutral-500 leading-relaxed'>
												{alt.description}
											</p>
										</button>
									);
								})}
							</div>

							<button
								onClick={handleApply}
								disabled={!selectedId}
								className='btn btn-ai self-end disabled:opacity-50 disabled:cursor-not-allowed'
							>
								<Ai color='' size={18} />
								Aplicar sugerencia
							</button>
						</div>
					)}
				</div>
			)}
		</>
	);
};

export default CharacteristicModal;

const ErrorState = () => (
	<div className='max-w-md w-full mx-4 px-6 py-8 bg-neutral-0 border border-neutral-200 shadow-lg rounded-xl flex flex-col items-center gap-4'>
		<h2 className='text-center text-neutral-800 text-lg font-semibold'>
			No se pudieron cargar las sugerencias
		</h2>
		<p className='text-neutral-500 text-sm text-center'>
			Hubo un problema al obtener las ideas. Por favor, inténtalo de nuevo.
		</p>
	</div>
);
