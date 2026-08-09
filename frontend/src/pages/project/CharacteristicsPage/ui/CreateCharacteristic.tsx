'use client';

import { Ai, Loading, Send } from '@/shared/ui';
import type { SuggestCharacteristic } from '@/entities/characteristic';
import { useCreateCharacteristic } from '../hooks/use-create-characteristic';
import CharacteristicModal from './CharacteristicModal';

interface Props {
	onCreated?: () => void;
}

const CreateCharacteristic = ({ onCreated }: Props) => {
	const {
		titleValue,
		titleOnBlur,
		titleRef,
		descValue,
		descOnBlur,
		descRef,
		titleCount,
		descCount,
		titleOver,
		descOver,
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
		handleForceCreate,
		closeConsistencyModal,
	} = useCreateCharacteristic(onCreated);

	return (
		<>
			{isValidating && (
				<Loading
					title='Verificando característica'
					description='La IA está analizando la coherencia de la característica con el descubrimiento del proyecto.'
					messages={[
						'Analizando coherencia con el descubrimiento...',
						'Derivando origen de la característica...',
						'Verificando reglas de negocio...',
					]}
				/>
			)}

			<div className='flex-1 px-0.5 flex flex-col gap-6'>
				<div className='w-full flex flex-col gap-3'>
					<h2 className='text-3xl font-bold text-base-800'>Crear una Característica</h2>
					<p className='text-lg text-base-600'>
						Define la interacción y el propósito de la nueva funcionalidad
					</p>
				</div>

				<form
					onSubmit={handleSubmit}
					className='flex-1 w-full rounded-lg bg-white p-8 mb-8 outline outline-gray-200 flex flex-col gap-6'
				>
					<div className='flex items-center gap-4'>
						<p className='flex-1 text-base'>
							La IA generará una especificación exhaustiva basada en tu descripción
						</p>

						<button type='button' onClick={openSuggestionsModal} className='btn btn-ai'>
							<Ai color='' size={20} />
							<span>Generar sugerencias</span>
						</button>
					</div>

					<div className='flex-1 flex flex-col gap-6'>
						<div className='flex flex-col gap-2'>
							<label className='text-lg font-medium'>Título*</label>
							{fieldErrors.title && (
								<p className='text-sm text-status-error'>{fieldErrors.title}</p>
							)}
							<p className='text-base text-base-800'>
								Expresa la intención de interacción del usuario (sin términos técnicos)
							</p>

							<div
								className={`flex flex-col rounded-lg bg-white px-4 py-4 outline-2 ${fieldErrors.title ? 'outline-status-error' : 'outline-base-800'}`}
							>
								<input
									ref={titleRef}
									type='text'
									value={titleValue}
									onChange={handleTitleChange}
									onBlur={titleOnBlur}
									maxLength={50}
									placeholder='Ej. Categorización inteligente de consumos'
									className='bg-transparent outline-none border-none focus:outline-none focus:ring-0'
								/>
								<span
									className={`self-end font-mono text-sm ${titleOver ? 'text-status-error' : 'text-base-600'}`}
								>
									{titleCount}/50
								</span>
							</div>
						</div>

						<div className='flex-1 flex flex-col gap-2'>
							<label className='text-lg font-medium'>Descripción*</label>
							{fieldErrors.description && (
								<p className='text-sm text-status-error'>{fieldErrors.description}</p>
							)}
							<p className='text-base text-base-800'>
								Describe cómo el usuario interactúa con el producto
							</p>

							<div
								className={`flex flex-1 flex-col rounded-lg bg-white p-4 outline-2 overflow-hidden ${fieldErrors.description ? 'outline-status-error' : 'outline-base-800'}`}
							>
								<textarea
									ref={descRef}
									value={descValue}
									onChange={handleDescChange}
									onBlur={descOnBlur}
									maxLength={500}
									placeholder='Ej. Asigna automáticamente una categoría (como alimentación, transporte, alojamiento o servicios) a cada gasto registrado basándose en el historial del grupo y el concepto ingresado. Esto facilita a los usuarios visualizar y analizar en qué rubros se está invirtiendo el dinero durante un viaje o periodo compartido.'
									className='flex-1 resize-none overflow-y-auto bg-transparent outline-none border-none focus:outline-none focus:ring-0'
								/>
								<span
									className={`self-end font-mono text-sm ${descOver ? 'text-status-error' : 'text-base-600'}`}
								>
									{descCount}/500
								</span>
							</div>
						</div>

						<div className='flex items-center justify-center gap-4'>
							<button type='button' onClick={handleCancel} className='btn btn-secondary'>
								<span>Cancelar</span>
							</button>
							<button type='submit' className='btn btn-primary'>
								<Send color='rotate-310' size={20} />
								<span>Crear característica</span>
							</button>
						</div>
					</div>
				</form>

				{showSuggestionsModal && (
					<CharacteristicModal
						onClose={closeSuggestionsModal}
						onApply={(selected: SuggestCharacteristic) => {
							applySuggestion(selected.title, selected.description);
						}}
					/>
				)}

				{showConsistencyModal && consistencyInfo && (
					<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50'>
						<div className='bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6 flex flex-col gap-4'>
							<h3 className='text-xl font-semibold text-base-800'>
								Revisión de coherencia
							</h3>
							<p className='text-base text-base-600'>
								La IA detectó que esta característica podría no alinearse con el
								descubrimiento:
							</p>
							<div className='bg-status-error/10 border border-status-error/30 rounded-md p-3'>
								<p className='text-sm text-status-error'>{consistencyInfo.reason}</p>
							</div>
							<div className='flex flex-col gap-1'>
								<label className='text-sm font-medium text-base-800'>
									Origen derivado:
								</label>
								<input
									type='text'
									className='w-full px-3 py-2 border border-base-200 rounded-md bg-base-50 text-base-800 text-sm'
									defaultValue={consistencyInfo.origin}
								/>
							</div>
							<div className='flex justify-end gap-3 pt-2'>
								<button
									type='button'
									onClick={closeConsistencyModal}
									className='btn btn-secondary'
								>
									Cancelar
								</button>
								<button
									type='button'
									onClick={handleForceCreate}
									className='btn btn-primary'
								>
									Forzar guardado
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
