'use client';

import { Ai, Send } from '@/shared/ui';
import type { AlternativeCharacteristic } from '@/entities/characteristic';
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
		applySuggestion,
	} = useCreateCharacteristic(onCreated);

	return (
		<div className='flex-1 px-0.5 flex flex-col gap-6'>
			<div className='w-full px-2 flex flex-col gap-2'>
				<h2 className='text-3xl font-bold text-base-800'>Crear una Característica</h2>
				<p className='text-lg font-medium text-base-800'>
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

					<button
						type='button'
						onClick={openSuggestionsModal}
						className='flex items-center gap-2 rounded-sm bg-ai hover:bg-ai/90 px-2.5 py-1 cursor-pointer'
					>
						<Ai color='text-base-50' size={20} />
						<span className='text-base text-base-50'>Generar sugerencias</span>
					</button>
				</div>

				<div className='flex-1 flex flex-col gap-6'>
					<div className='flex flex-col gap-2'>
						<label className='text-lg font-medium'>Título*</label>
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

					<button
						type='submit'
						className='self-center flex items-center gap-1 rounded-sm bg-primary-100 px-2.5 py-1 cursor-pointer'
					>
						<Send color='text-base-50 rotate-310' size={24} />
						<span className='text-base font-semibold text-base-50'>
							Crear característica
						</span>
					</button>
				</div>
			</form>

			{showSuggestionsModal && (
				<CharacteristicModal
					onClose={closeSuggestionsModal}
					onApply={(selected: AlternativeCharacteristic) => {
						applySuggestion(selected.title, selected.description);
					}}
				/>
			)}
		</div>
	);
};

export default CreateCharacteristic;
