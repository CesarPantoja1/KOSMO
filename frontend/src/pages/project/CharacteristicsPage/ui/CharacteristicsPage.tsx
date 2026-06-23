'use client';

import { useAppStore } from 'app/store/app.store';
import { Plus, toast } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { addCharacteristics, getCharacteristics } from '@/entities/characteristic';
import type { AlternativeCharacteristic, Characteristic } from '@/entities/characteristic';
import CardCharacterist from './CardCharacterist';
import CharacteristicModal from './CharacteristicModal';
import Search from './Search';

const CharacteristicsPage = () => {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [showModal, setShowModal] = useState(false);
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
				})),
			);
			setCharacteristics((prev) => [...prev, ...newChars]);
			setShowModal(false);
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al agregar características';
			toast.error(message);
		}
	};

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
						onClick={() => setShowModal(true)}
						className='inline-flex px-3.5 py-1.5 cursor-pointer gap-1.5 bg-ai rounded-sm'
					>
						<Plus color='text-base-50' size={24} />
						<span className='text-center justify-center text-base-50 font-semibold'>
							Característica
						</span>
					</button>

					<Link
						href='requisitos'
						className='inline-flex px-3.5 py-1.5 cursor-pointer gap-1.5 bg-ai rounded-sm'
					>
						<ArrowRight color='text-base-50' size={24} />
						<div className='text-center justify-center text-base-50'>Requisitos</div>
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
					{filtered.map((c) => (
						<CardCharacterist
							key={c.id}
							displayId={c.display_id}
							title={c.title}
							description={c.description}
							searchQuery={searchQuery}
						/>
					))}
				</div>
			)}

			{showModal && currentProject && (
				<CharacteristicModal
					projectId={currentProject.id}
					onClose={() => setShowModal(false)}
					onApply={handleApply}
				/>
			)}
		</div>
	);
};

export { CharacteristicsPage };
