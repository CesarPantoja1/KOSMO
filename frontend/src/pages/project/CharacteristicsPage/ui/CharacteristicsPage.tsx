import { ButtonMD } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import { Metadata } from 'next';
import { Edith, Search } from './icons';
import Trash from './icons/Trash';
import CardCharacterist from './CardCharacterist';

const metadata: Metadata = {
	title: 'Características - KOSMO',
	description: '',
};

const CharacteristicsPage = () => {
	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
			<div className='py-3.5 border-b-2 inline-flex justify-end items-center gap-2.5'>
				<div className='flex-1 inline-flex flex-col justify-start items-start gap-5'>
					<div className='flex flex-col justify-start items-start gap-5'>
						<div className='w-[735.50px] h-8 justify-center text-base-800 text-3xl font-bold'>
							Características
						</div>
						<div className='justify-center text-base-800 text-lg font-medium'>
							Gestiona y organiza las funciones principales de tu proyecto. Tienes el
							control total para editar, eliminar o añadir nuevas características según
							tus necesidades.
						</div>
					</div>
					<div className='h-10 inline-flex justify-start items-center gap-4'>
						<div
							data-propiedad-1='search'
							className='px-2 py-3.5 outline outline-offset-1 outline-base-800 flex justify-start items-center gap-2.5'
						>
							<div className='size-8 relative overflow-hidden'>
								<div className='size-6 left-[4px] top-[4px] absolute outline outline-[1.50px] outline-offset-[-0.75px] outline-neutral-400' />
							</div>
							<div className='justify-start text-neutral-400 text-base font-semibold'>
								Buscar Característica
							</div>
						</div>
						<div className='flex-1 flex justify-end items-center gap-4'>
							<div
								data-propiedad-1='boton-feature'
								className='px-3 py-4 relative rounded-sm inline-flex flex-col justify-start items-start gap-2.5'
							>
								<div className='w-44 h-10 left-0 top-0 absolute bg-ai rounded-sm' />
								<div className='flex-1 inline-flex justify-center items-center gap-2.5'>
									<div className='size-6 relative overflow-hidden'>
										<div className='size-6 left-0 top-0 absolute bg-base-50 border border-base-50' />
									</div>
									<div className='text-center justify-center text-base-50 text-base font-semibold'>
										Característica
									</div>
								</div>
							</div>
							<div
								data-propiedad-1='boton-feature'
								className='px-3 py-4 relative rounded-sm inline-flex flex-col justify-start items-start gap-2.5'
							>
								<div className='w-36 h-10 left-0 top-0 absolute bg-ai rounded-sm' />
								<div className='flex-1 inline-flex justify-center items-center gap-2.5'>
									<div className='size-6 relative overflow-hidden'>
										<div className='w-4 h-3.5 left-[3px] top-[4.50px] absolute outline outline-[1.50px] outline-offset-[-0.75px] outline-base-50' />
									</div>
									<div className='text-center justify-center text-base-50 text-base font-semibold'>
										Requisitos
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div>
				<CardCharacterist />
			</div>

			<div className='flex items-center justify-between'>
				<h2 className='shrink-0 text-2xl'>Características</h2>
				<ButtonMD variant='ai'>Regenerar</ButtonMD>

				<ArrowRight color='text-primary-50' size={24} />
				<Search color='text-primary-50' />
			</div>
		</div>
	);
};

export { CharacteristicsPage, metadata };
