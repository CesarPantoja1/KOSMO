'use client';

import { Plus } from '@/shared/ui';

import Link from 'next/link';
import { useState } from 'react';
import { Cards, Clock, List } from './icons';

const stylesButtonToggle = {
	on: {
		button: 'bg-primary-100 border-base-950',
		icon: 'text-base-50',
	},
	off: {
		button: 'bg-base-50 outline outline-1 outline-base-600',
		icon: 'text-base-600',
	},
};

type viewStyles = {
	list: {
		button: string;
		icon: string;
	};
	card: {
		button: string;
		icon: string;
	};
};

export function HomePage() {
	const [isViewCardOn, setIsViewCardOn] = useState(true);
	const [stylesToogleView, setStylesToogleView] = useState<viewStyles>({
		list: stylesButtonToggle.off,
		card: stylesButtonToggle.on,
	});

	const setViewList = () => {
		setStylesToogleView({
			list: stylesButtonToggle.on,
			card: stylesButtonToggle.off,
		});
		setIsViewCardOn(false);
	};

	const setViewCard = () => {
		setStylesToogleView({
			list: stylesButtonToggle.off,
			card: stylesButtonToggle.on,
		});
		setIsViewCardOn(true);
	};

	return (
		<section className='flex flex-col gap-12 p-6'>
			<div className='flex flex-col gap-2.5'>
				<div className='justify-center text-base-800 text-3xl font-bold'>Proyectos</div>
				<div className='flex justify-between items-center gap-2.5'>
					<p className='text-base-600 text-xl font-light '>
						Gestiona y da seguimiento a tus iniciativas de producto
					</p>
					<p className='flex items-center gap-2'>
						<div className='flex'>
							<button
								onClick={setViewCard}
								className={`px-6 py-2.5 cursor-pointer ${stylesToogleView.card.button}`}
							>
								<Cards size={24} color={stylesToogleView.card.icon} />
							</button>
							<button
								onClick={setViewList}
								className={`px-6 py-2.5 cursor-pointer ${stylesToogleView.list.button}`}
							>
								<List size={24} color={stylesToogleView.list.icon} />
							</button>
						</div>

						<Link
							href='/crear-proyecto'
							className='flex gap-2 items-center px-3.5 py-1.5 text-base-50 text-base font-semibold bg-primary-100 rounded-sm '
						>
							<Plus color='text-base-50' />
							<span>PROYECTO</span>
						</Link>
					</p>
				</div>

				{isViewCardOn ? (
					<div className='bg-base-50 flex gap-2.5'>
						<Link
							href='/crear-proyecto'
							className='size- inline-flex justify-start items-center gap-10'
						>
							<div
								data-propiedad-1='create-project'
								className='w-96 h-40 px-5 pt-7 pb-2.5 bg-base-50 rounded-sm shadow-[0px_4px_8px_0px_rgba(0,0,0,0.20)] outline outline-1 outline-offset-[-1px] outline-black inline-flex flex-col justify-start items-start gap-4 overflow-hidden'
							>
								<div className='self-stretch flex flex-col justify-start items-start gap-3.5'>
									<div className='self-stretch inline-flex justify-center items-center gap-16'>
										<Plus color='text-base-600' />
									</div>
									<div className='self-stretch h-8 relative'>
										<div className="left-[45px] top-[-0.35px] absolute justify-start text-black text-2xl font-semibold font-['Geist']">
											Crear nuevo proyecto
										</div>
									</div>
									<div className='self-stretch inline-flex justify-center items-center gap-2.5'>
										<div className="justify-start text-base-600 text-base font-normal font-['Geist']">
											Crea algo innovador
										</div>
									</div>
								</div>
							</div>
						</Link>
					</div>
				) : (
					<div className='bg-base-50 flex flex-col gap-2.5'>
						<div className='self-stretch px-3 py-2 bg-base-100 border-b border-emerald-800 inline-flex justify-between items-start'>
							<div className="justify-start text-base-600 text-2xl font-semibold font-['Geist']">
								Proyecto
							</div>

							<div className="w-40 justify-start text-base-600 text-2xl font-semibold font-['Geist']">
								Etapa
							</div>
							<div className="justify-start text-base-600 text-2xl font-semibold font-['Geist']">
								Estado
							</div>
							<div className="justify-start text-base-600 text-2xl font-semibold font-['Geist']">
								Última actividad
							</div>
						</div>
						<div className='p-3 bg-white border-b border-emerald-800 flex justify-between items-center overflow-hidden'>
							<div className='flex flex-col gap-1.5'>
								<div className='justify-start text-base-950 text-base font-normal'>
									FERRETERÍA
								</div>
								<div className='justify-start text-base-600 text-base font-normal'>
									Plataforma de gestión de inventvario
								</div>
							</div>
							<div className='justify-start text-base-600 text-base font-normal'>
								Características
							</div>
							<div className='p-1 bg-primary-50 rounded-sm flex justify-center items-center gap-2.5'>
								<Clock size={24} color='text-primary-100' />
								<div className='justify-start text-primary-100 text-lg font-medium leading-8'>
									En progreso
								</div>
							</div>
							<div className=' text-base-600 text-base font-normal'>Hace 2 horas</div>
						</div>
					</div>
				)}
			</div>
		</section>
	);
}
