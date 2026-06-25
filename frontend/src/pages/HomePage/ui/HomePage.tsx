'use client';

import { Plus } from '@/shared/ui';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Cards, Clock, List } from './icons';
import { projectsApi } from '@/entities/project/api/projects-api';
import { useAppStore } from 'app/store/app.store';
import { Project } from '@/entities/project/model/types';

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
	const router = useRouter();
	const { setProjectState } = useAppStore();
	const resetProjectState = useAppStore((s) => s.resetProjectState);
	const [projects, setProjects] = useState<Project[]>([]);
	const [loading, setLoading] = useState(true);

	const [isViewCardOn, setIsViewCardOn] = useState(true);
	const [stylesToogleView, setStylesToogleView] = useState<viewStyles>({
		list: stylesButtonToggle.off,
		card: stylesButtonToggle.on,
	});

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				const data = await projectsApi.getProjects();
				setProjects(data);
			} catch (error) {
				console.error('Failed to load projects', error);
			} finally {
				setLoading(false);
			}
		};
		resetProjectState();
		fetchProjects();
	}, [resetProjectState]);

	const handleProjectClick = (project: Project) => {
		setProjectState(project);
		router.push('/proyecto/descubrimiento');
	};

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
					<div className='flex items-center gap-2'>
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
					</div>
				</div>

				{loading ? (
					<div>Cargando proyectos...</div>
				) : isViewCardOn ? (
					<div className='flex gap-4 flex-wrap'>
						<Link
							href='/crear-proyecto'
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
						</Link>

						{projects.map((project) => (
							<div
								key={project.id}
								onClick={() => handleProjectClick(project)}
								className='w-96 h-40 px-5 pt-7 pb-2.5 bg-white cursor-pointer hover:bg-gray-50 rounded-sm shadow-[0px_4px_8px_0px_rgba(0,0,0,0.20)] outline outline-1 outline-offset-[-1px] outline-base-200 inline-flex flex-col justify-start items-start gap-4 overflow-hidden transition-all'
							>
								<div className='self-stretch flex flex-col justify-start items-start gap-3.5'>
									<div className='self-stretch h-8 relative'>
										<div className='left-0 top-0 absolute justify-start text-black text-2xl font-semibold truncate w-full'>
											{project.name}
										</div>
									</div>
									<div className='self-stretch inline-flex justify-start items-center gap-2.5 line-clamp-2'>
										<div className='justify-start text-base-600 text-base font-normal'>
											{project.description || 'Sin descripción'}
										</div>
									</div>
								</div>
							</div>
						))}
					</div>
				) : (
					<div className='bg-base-100/15 flex flex-col gap-2.5'>
						<table className='w-full'>
							<thead>
								<tr className='bg-base-100 border-b border-primary-800'>
									<th className='px-3 py-2 text-left text-base-600 text-2xl font-semibold'>
										Proyecto
									</th>
									<th className='w-40 px-3 py-2 text-left text-base-600 text-2xl font-semibold'>
										Fase Actual
									</th>
									<th className='w-40 px-3 py-2 text-center text-base-600 text-2xl font-semibold'>
										Estado
									</th>
									<th className='w-40 px-3 py-2 text-right text-base-600 text-2xl font-semibold'>
										Creado
									</th>
								</tr>
							</thead>

							<tbody>
								{projects.length === 0 && (
									<tr>
										<td colSpan={4} className='p-4 bg-white text-center text-base-600'>
											No tienes proyectos creados.
										</td>
									</tr>
								)}

								{projects.map((project) => (
									<tr
										key={project.id}
										onClick={() => handleProjectClick(project)}
										className='cursor-pointer border-b border-primary-800 bg-white transition-all'
									>
										<td className='p-3'>
											<div className='flex flex-col gap-1.5'>
												<div className='text-base-950 text-base font-medium truncate'>
													{project.name}
												</div>
												<div className='text-base-600 text-sm truncate'>
													{project.description || 'Sin descripción'}
												</div>
											</div>
										</td>

										<td className='w-40 p-3 text-base-600 text-base capitalize'>
											{project.current_phase || 'Descubrimiento'}
										</td>

										<td className='w-40 p-3'>
											<div className='flex justify-center'>
												<div className='p-1 px-3 bg-primary-50 rounded-sm flex items-center gap-2.5'>
													<Clock size={16} color='text-primary-100' />
													<span className='text-primary-100 text-sm font-medium'>
														{project.status || 'En progreso'}
													</span>
												</div>
											</div>
										</td>

										<td className='w-40 p-3 text-right text-base-600 text-sm'>
											<time dateTime={project.created_at}>
												{new Date(project.created_at).toLocaleDateString()}
											</time>
										</td>
									</tr>
								))}
							</tbody>
						</table>

						<Link href='/crear-proyecto' className='p-3 inline-flex items-center gap-3'>
							<div className='p-1 rounded-sm outline outline-base-600'>
								<Plus color='text-base-600' />
							</div>
							<span className='text-base-950 text-xl'>Crear nuevo proyecto</span>
						</Link>
					</div>
				)}
			</div>
		</section>
	);
}
