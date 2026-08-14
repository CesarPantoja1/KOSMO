'use client';

import type { SuggestCharacteristic } from '@/entities/characteristic';
import { Ai, CharacterCounter, Loading, Send } from '@/shared/ui';
import { useCreateCharacteristic } from '../hooks/use-create-characteristic';
import CharacteristicModal from './CharacteristicModal';

const CreateCharacteristic = () => {
	const {
		titleValue,
		titleOnBlur,
		titleRef,
		descValue,
		descOnBlur,
		descRef,
		titleCount,
		descCount,
		fieldErrors,
		showSuggestionsModal,
		openSuggestionsModal,
		closeSuggestionsModal,
		handleTitleChange,
		handleDescChange,
		handleSubmit,
		handleCancel,
		applySuggestion,
		showConsistencyModal,
		consistencyInfo,
		isValidating,
		closeConsistencyModal,
	} = useCreateCharacteristic();

	return (
		<>
			{isValidating && (
				<Loading
					title='Verificando funcionalidad'
					description='El asistente está analizando la coherencia de la funcionalidad con el descubrimiento del proyecto.'
					messages={[
						'Analizando coherencia con el descubrimiento...',
						'Derivando origen de la funcionalidad...',
						'Verificando reglas de negocio...',
					]}
				/>
			)}

			<div className='page-container'>
				<div className='page-header'>
					{/* Header row — título a la izquierda, sugerir ideas a la derecha */}
					<div className='flex flex-col gap-4'>
						<div className='flex justify-between items-start gap-4'>
							<div className='flex flex-col gap-1'>
								<h2 className='text-neutral-800 text-3xl font-bold'>
									Nueva funcionalidad
								</h2>
								<p className='text-neutral-500 text-base'>
									Define el propósito e interacción de la nueva funcionalidad
								</p>
							</div>
							<button
								type='button'
								onClick={openSuggestionsModal}
								className='btn btn-ai shrink-0'
							>
								<Ai color='' size={18} />
								Sugerir ideas
							</button>
						</div>
					</div>

					<form
						id='create-characteristic-form'
						onSubmit={handleSubmit}
						className='flex flex-col gap-6 rounded-xl bg-neutral-0 p-8 border border-neutral-200 shadow-sm'
					>
						<div className='flex flex-col gap-5'>
							{/* Title field */}
							<div className='flex flex-col gap-2'>
								<label className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'>
									Título <span className='text-error-500'>*</span>
								</label>
								<p className='text-xs text-neutral-400'>
									Expresa la intención del usuario sin términos técnicos
								</p>
								<input
									ref={titleRef}
									type='text'
									value={titleValue}
									onChange={handleTitleChange}
									onBlur={titleOnBlur}
									maxLength={50}
									placeholder='Ej. Categorización inteligente de consumos'
									className={`w-full min-h-11 px-4 py-2.5 text-neutral-800 placeholder:text-neutral-400 bg-neutral-50 border rounded-md focus:ring-2 focus:outline-none transition-all duration-200 ${
										fieldErrors.title
											? 'border-error-500 ring-2 ring-error-500/15'
											: 'border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20'
									}`}
								/>
								<div className='flex justify-between items-center gap-2'>
									{fieldErrors.title ? (
										<p className='text-error-500 text-xs' role='alert'>
											{fieldErrors.title}
										</p>
									) : (
										<span />
									)}
									<CharacterCounter current={titleCount} max={50} />
								</div>
							</div>

							{/* Description field */}
							<div className='flex flex-col gap-2'>
								<label className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'>
									Descripción <span className='text-error-500'>*</span>
								</label>
								<p className='text-xs text-neutral-400'>
									Describe cómo el usuario interactúa con el producto
								</p>
								<textarea
									ref={descRef}
									value={descValue}
									onChange={handleDescChange}
									onBlur={descOnBlur}
									maxLength={500}
									rows={6}
									placeholder='Ej. Asigna automáticamente una categoría a cada gasto registrado basándose en el historial del grupo y el concepto ingresado...'
									className={`w-full min-h-40 px-4 py-3 text-neutral-800 placeholder:text-neutral-400 bg-neutral-50 border rounded-md focus:ring-2 focus:outline-none transition-all duration-200 resize-none ${
										fieldErrors.description
											? 'border-error-500 ring-2 ring-error-500/15'
											: 'border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20'
									}`}
								/>
								<div className='flex justify-between items-center gap-2'>
									{fieldErrors.description ? (
										<p className='text-error-500 text-xs' role='alert'>
											{fieldErrors.description}
										</p>
									) : (
										<span />
									)}
									<CharacterCounter current={descCount} max={500} />
								</div>
							</div>

							{/* Actions — al final del formulario */}
							<div className='flex items-center justify-end gap-3 pt-2'>
								<button
									type='button'
									onClick={handleCancel}
									className='btn btn-secondary'
								>
									Cancelar
								</button>
								<button type='submit' className='btn btn-primary'>
									<Send color='rotate-310' size={18} />
									Crear funcionalidad
								</button>
							</div>
						</div>
					</form>
				</div>

				{showSuggestionsModal && (
					<CharacteristicModal
						onClose={closeSuggestionsModal}
						onApply={(selected: SuggestCharacteristic) => {
							applySuggestion(selected.title, selected.description);
						}}
					/>
				)}

				{showConsistencyModal && consistencyInfo && (
					<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/40'>
						<div className='bg-neutral-0 rounded-xl shadow-lg max-w-md w-full mx-4 p-6 border border-neutral-200 flex flex-col gap-4'>
							<h3 className='text-lg font-semibold text-neutral-800'>
								Revisión de coherencia
							</h3>
							<p className='text-sm text-neutral-500'>
								El asistente detectó que esta funcionalidad no se alinea con el
								descubrimiento del proyecto. Para guardarla, modifica primero el
								documento de Descubrimiento:
							</p>
							<div className='bg-error-50 border border-error-500/30 rounded-md p-3'>
								<p className='text-sm text-error-700'>{consistencyInfo.reason}</p>
							</div>
							<div className='flex justify-end gap-3 pt-1'>
								<button
									type='button'
									onClick={closeConsistencyModal}
									className='btn btn-primary'
								>
									Entendido
								</button>
							</div>
						</div>
					</div>
				)}
			</div>
		</>
	);
};

export default CreateCharacteristic;
