'use client';

import { Plus } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import Link from 'next/link';
import { useCharacteristicsPage } from '../hooks/use-characteristics-page';
import CardCharacterist from './CardCharacterist';
import Search from './Search';
import CreateCharacteristic from './CreateCharacteristic';

const CharacteristicsPage = () => {
	const { view, setView, characteristics, isLoading, searchQuery, setSearchQuery, filtered } =
		useCharacteristicsPage();

	if (view === 'create') {
		return (
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
				<CreateCharacteristic onCreated={() => setView('list')} />
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
