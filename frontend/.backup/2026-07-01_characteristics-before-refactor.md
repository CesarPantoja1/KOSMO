# Backup: Características (pre-modo-single-select)
## Date: 2026-07-01

### CharacteristicsPage.tsx v2

```tsx
'use client';

import { useAppStore } from 'app/store/app.store';
import { Plus, toast } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { addCharacteristics, getCharacteristics } from '@/entities/characteristic';
import type {
	AlternativeCharacteristic,
	Characteristic,
} from '@/entities/characteristic';
import CardCharacterist from './CardCharacterist';
import Search from './Search';
import CreateCharacteristic from './CreateCharacteristic';

const CharacteristicsPage = () => {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [view, setView] = useState<'list' | 'create'>('list');
	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [searchQuery, setSearchQuery] = useState('');

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetchData = async () => {
			try {
				const data = await getCharacteristics(currentProject.id);
				setCharacteristics(data);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : 'Error al cargar las características';
				toast.error(message);
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [currentProject, router]);

	const filtered = searchQuery.trim()
		? characteristics.filter((c) =>
				c.title.toLowerCase().includes(searchQuery.toLowerCase()),
			)
		: characteristics;

	const handleApply = async (selected: AlternativeCharacteristic[]) => {
		if (!currentProject) return;
		try {
			const newChars = await addCharacteristics(
				currentProject.id,
				selected.map((s) => ({
					title: s.title,
					description: s.description,
					rationale: s.rationale,
					inferred_from: s.inferred_from,
				})),
			);
			setCharacteristics((prev) => [...prev, ...newChars]);
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al agregar características';
			toast.error(message);
		}
	};

	if (view === 'create' && currentProject) {
		return (
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
				<CreateCharacteristic
					projectId={currentProject.id}
					onCreated={() => setView('list')}
					onApplySuggestions={handleApply}
				/>
			</div>
		);
	}

	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
			<div className='flex flex-col justify-start items-start gap-5'>
				<h2 className='h-8 justify-center text-base-800 text-3xl font-bold'>
					Características
				</h2>
				<div className='justify-center text-base-800 text-lg font-medium'>
					Gestiona y organiza las funciones principales de tu proyecto. Tienes el control
					total para editar, eliminar o añadir nuevas características según tus
					necesidades.
				</div>
			</div>

			<div className='h-10 inline-flex justify-between items-center gap-4'>
				<Search value={searchQuery} onChange={setSearchQuery} />
				<div className='flex justify-end items-center gap-4'>
					<button
						onClick={() => setView('create')}
						className='inline-flex items-center px-3.5 py-1.5 cursor-pointer gap-1.5 bg-primary-100 hover:bg-primary-100/90 rounded-sm'
					>
						<Plus color='text-base-50' size={20} />
						<span className='text-center justify-center text-base-50'>
							Nueva Característica
						</span>
					</button>

					<Link
						href='requisitos'
						className='inline-flex items-center px-3.5 py-1.5 cursor-pointer gap-1.5 bg-primary-100 hover:bg-primary-100/90 rounded-sm'
					>
						<div className='text-center justify-center text-base-50'>Ir a Requisitos</div>
						<ArrowRight color='text-base-50' size={20} />
					</Link>
				</div>
			</div>

			{isLoading && (
				<div className='overflow-y-auto flex flex-col gap-4 pb-4'>
					{[1, 2, 3, 4, 5].map((i) => (
						<div
							key={i}
							className='outline outline-base-300 m-0.5 p-8 inline-flex justify-start items-center gap-7 animate-pulse'
						>
							<div className='w-14 h-10 bg-base-200 rounded' />
							<div className='flex-1 flex flex-col gap-3'>
								<div className='h-6 bg-base-200 rounded w-3/4' />
								<div className='h-4 bg-base-200 rounded w-full' />
							</div>
						</div>
					))}
				</div>
			)}

			{!isLoading && (
				<div className='overflow-y-auto flex flex-col gap-4 pb-4'>
					{filtered.length === 0 && searchQuery.trim() ? (
						<div className='outline outline-base-300 m-0.5 px-8 py-16 flex flex-col justify-center items-center gap-4'>
							<p className='text-base-600 text-lg font-medium text-center'>
								No se encontraron características que coincidan con su búsqueda
							</p>
						</div>
					) : (
						filtered.map((c) => (
							<CardCharacterist
								key={c.id}
								displayId={c.display_id}
								title={c.title}
								description={c.description}
								searchQuery={searchQuery}
							/>
						))
					)}
				</div>
			)}
		</div>
	);
};

export { CharacteristicsPage };
```

### CreateCharacteristic.tsx v2

```tsx
'use client';

import { useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Ai, Send } from '@/shared/ui';
import type { AlternativeCharacteristic } from '@/entities/characteristic';
import CharacteristicModal from './CharacteristicModal';

const characteristicSchema = z.object({
	title: z.string().max(50, 'Máximo 50 caracteres'),
	description: z.string().max(500, 'Máximo 500 caracteres'),
});

type CharacteristicFormData = z.infer<typeof characteristicSchema>;

interface Props {
	projectId: string;
	onCreated?: () => void;
	onApplySuggestions?: (selected: AlternativeCharacteristic[]) => void;
}

const CreateCharacteristic = ({ projectId, onCreated, onApplySuggestions }: Props) => {
	const { control, handleSubmit } = useForm<CharacteristicFormData>({
		mode: 'onChange',
		resolver: zodResolver(characteristicSchema),
		defaultValues: { title: '', description: '' },
	});

	const {
		field: {
			value: titleValue,
			onChange: titleOnChange,
			onBlur: titleOnBlur,
			ref: titleRef,
		},
	} = useController({ name: 'title', control });

	const {
		field: { value: descValue, onChange: descOnChange, onBlur: descOnBlur, ref: descRef },
	} = useController({ name: 'description', control });

	const [showSuggestionsModal, setShowSuggestionsModal] = useState(false);

	const titleCount = titleValue.length;
	const descCount = descValue.length;
	const titleOver = titleCount > 50;
	const descOver = descCount > 500;

	const onSubmit = () => {
		onCreated?.();
	};

	return (
		<div className='flex-1 px-0.5 flex flex-col gap-6'>
			<div className='w-full px-2 flex flex-col gap-2'>
				<h2 className='text-3xl font-bold text-base-800'>Crear una Característica</h2>
				<p className='text-lg font-medium text-base-800'>
					Define la interacción y el propósito de la nueva funcionalidad
				</p>
			</div>

			<form
				onSubmit={handleSubmit(onSubmit)}
				className='flex-1 w-full rounded-lg bg-white p-8 mb-8 outline outline-gray-200 flex flex-col gap-6'
			>
				<div className='flex items-center gap-4'>
					<p className='flex-1 text-base'>
						La IA generará una especificación exhaustiva basada en tu descripción
					</p>

					<button
						type='button'
						onClick={() => setShowSuggestionsModal(true)}
						className='flex items-center gap-2 rounded-sm bg-ai hover:bg-ai/90 px-2.5 py-1 cursor-pointer'
					>
						<Ai color='text-base-50' size={24} />
						<span className='text-base text-base-50'>Generar sugerencias</span>
					</button>
				</div>

				<div className='flex-1 flex flex-col gap-6'>
					{/* Título */}
					<div className='flex flex-col gap-2'>
						<label className='text-lg font-medium'>Título*</label>

						<p className='text-base text-base-800'>
							Expresa la intención de interacción del usuario (sin términos técnicos)
						</p>

						<div className='flex flex-col rounded-lg bg-white px-4 py-4 outline-2 outline-base-800'>
							<input
								ref={titleRef}
								type='text'
								value={titleValue}
								onChange={titleOnChange}
								onBlur={titleOnBlur}
								placeholder='Ej. Categorización inteligente de consumos'
								className='bg-transparent outline-none border-none focus:outline-none focus:ring-0'
							/>

							<span
								className={`self-end font-mono text-sm ${
									titleOver ? 'text-status-error' : 'text-base-600'
								}`}
							>
								{titleCount}/50
							</span>
						</div>
					</div>

					{/* Descripción */}
					<div className='flex-1 flex flex-col gap-2'>
						<label className='text-lg font-medium'>Descripción*</label>

						<p className='text-base text-base-800'>
							Describe cómo el usuario interactúa con el producto
						</p>

						<div className='flex flex-1 flex-col rounded-lg bg-white p-4 outline-2 outline-base-800 overflow-hidden'>
							<textarea
								ref={descRef}
								value={descValue}
								onChange={descOnChange}
								onBlur={descOnBlur}
								placeholder='Ej. Asigna automáticamente una categoría (como alimentación, transporte, alojamiento o servicios) a cada gasto registrado basándose en el historial del grupo y el concepto ingresado. Esto facilita a los usuarios visualizar y analizar en qué rubros se está invirtiendo el dinero durante un viaje o periodo compartido.'
								className='flex-1 resize-none overflow-y-auto bg-transparent outline-none border-none focus:outline-none focus:ring-0'
							/>

							<span
								className={`self-end font-mono text-sm ${
									descOver ? 'text-status-error' : 'text-base-600'
								}`}
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
					projectId={projectId}
					onClose={() => setShowSuggestionsModal(false)}
					onApply={(selected) => {
						onApplySuggestions?.(selected);
						setShowSuggestionsModal(false);
					}}
				/>
			)}
		</div>
	);
};

export default CreateCharacteristic;
```

### CharacteristicModal.tsx v2

```tsx
import { Ai, Close, Loading } from '@/shared/ui';
import { useState, useEffect } from 'react';
import { getAlternativeCharacteristics } from '@/entities/characteristic';
import type { AlternativeCharacteristic } from '@/entities/characteristic';

type Props = {
	projectId: string;
	onClose: () => void;
	onApply: (selected: AlternativeCharacteristic[]) => void;
};

const CharacteristicModal = ({ projectId, onClose, onApply }: Props) => {
	const [alternatives, setAlternatives] = useState<AlternativeCharacteristic[]>([]);
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);

	useEffect(() => {
		const fetch = async () => {
			setIsLoading(true);
			setHasError(false);
			try {
				const data = await getAlternativeCharacteristics(projectId);
				setAlternatives(data);
			} catch {
				setHasError(true);
			} finally {
				setIsLoading(false);
			}
		};
		fetch();
	}, [projectId]);

	const toggle = (id: string) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	const handleApply = () => {
		const selected = alternatives.filter((a) => selectedIds.has(a.id));
		if (selected.length === 0) return;
		onApply(selected);
	};

	return (
		<div
			className='fixed inset-0 z-50 flex items-center justify-center bg-black/60'
			onClick={onClose}
		>
			{isLoading && (
				<Loading
					title='Nuevas Características'
					description='Buscando sugerencias para tu proyecto...'
				/>
			)}

			{hasError && <ErrorState />}

			{!isLoading && !hasError && (
				<div
					className='bg-base-50 w-1/2 p-7 rounded-md flex flex-col items-center gap-4'
					onClick={(e) => e.stopPropagation()}
				>
					<div className='w-full flex flex-col gap-4'>
						<div className='flex justify-between'>
							<h2 className='text-2xl font-semibold'>Sugerencias de Características</h2>
							<button className='cursor-pointer' onClick={onClose}>
								<Close color='text-base-600 hover:text-status-error' size={24} />
							</button>
						</div>
						<p className='flex-1 text-base font-normal'>
							Ideas de funciones impulsadas por IA basadas en el contexto de tu producto.
						</p>
					</div>

					<div className='w-full flex-1 p-0.5 flex flex-col justify-start items-center gap-5'>
						{alternatives.map((alt) => {
							const isSelected = selectedIds.has(alt.id);
							return (
								<button
									key={alt.id}
									onClick={() => toggle(alt.id)}
									className={`w-full p-5 flex flex-col items-start gap-3 cursor-pointer rounded-sm text-left transition-shadow duration-200 ${
										isSelected
											? 'outline-2 outline-primary-100 shadow-md bg-primary-100/5'
											: 'outline-1 outline-base-300 hover:shadow-lg hover:outline-primary-100'
									}`}
								>
									<h3 className='text-primary-100 text-lg font-semibold'>{alt.title}</h3>
									<p className='text-base font-normal'>{alt.description}</p>
								</button>
							);
						})}
					</div>

					<button
						onClick={handleApply}
						disabled={selectedIds.size === 0}
						className='inline-flex items-center gap-1 px-5 py-1 w-fit cursor-pointer text-base-50 outline outline-ai bg-ai rounded-sm  transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed'
					>
						<Ai color='text-base-50' size={20} />
						Aplicar
					</button>
				</div>
			)}
		</div>
	);
};

export default CharacteristicModal;

const ErrorState = () => (
	<div className='w-1/2 px-5 py-7 bg-base-50 outline outline-base-300 inline-flex flex-col justify-center rounded-md items-center gap-7'>
		<h2 className='text-center justify-start text-black text-2xl font-semibold'>
			⚠️ No se pudieron cargar las sugerencias.
		</h2>
		<p className='text-black text-lg text-center'>
			Hubo un fallo al obtener las características sugeridas. Inténtalo de nuevo.
		</p>
	</div>
);
```
