'use client';

import { Plus } from '@/shared/ui';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Cards, Clock, List } from './icons';
import { getProjects } from '@/entities/project/api/api';
import { useAppStore } from 'app/store/app.store';
import { Project } from '@/entities/project/model/types';
import { TableFooter } from 'react-aria-components';

const stylesButtonToggle = {
	on: {
		button: 'bg-primary-100 border-primary-800 shadow-sm scale-100',
		icon: 'text-base-50',
	},
	off: {
		button: 'bg-base-50 outline outline-1 outline-base-300 hover:bg-base-100 scale-95',
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
				const data = await getProjects();
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

	const initializeProject = useAppStore((s) => s.initializeProject);

	const handleProjectClick = (project: Project) => {
		setProjectState(project);
		initializeProject(project.id);
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
		<section className='page-container mt-6'>
			<div className='page-header mb-8'>
				<h2 className='text-base-800 text-3xl font-bold'>Proyectos</h2>
				<p className='text-base-600 text-xl font-light'>
					Gestiona y da seguimiento a tus iniciativas de producto
				</p>
				<div className='flex self-end gap-2'>
					<div className='flex'>
						<button
							onClick={setViewCard}
							className={`px-6 py-2.5 cursor-pointer rounded-sm transition-all duration-200 ease-in-out ${stylesToogleView.card.button}`}
						>
							<Cards size={24} color={stylesToogleView.card.icon} />
						</button>
						<button
							onClick={setViewList}
							className={`px-6 py-2.5 cursor-pointer rounded-sm transition-all duration-200 ease-in-out ${stylesToogleView.list.button}`}
						>
							<List size={24} color={stylesToogleView.list.icon} />
						</button>
					</div>

					<Link
						href='/crear-proyecto'
						className='flex gap-2 items-center px-3.5 py-1.5 text-base-50 text-base font-semibold bg-primary-100 rounded-sm transition-all duration-200 ease-in-out hover:bg-primary-800 hover:shadow-md active:scale-95'
					>
						<Plus color='text-base-50' />
						<span>PROYECTO</span>
					</Link>
				</div>

				<div className='flex gap-y-6 gap-x-2 pb-8 items-start flex-wrap overflow-y-auto relative'>
					{loading ? (
						<>
							{Array.from({ length: 6 }).map((_, index) => (
								<div
									key={index}
									className='flex h-40 w-96 mx-auto my-1 flex-col rounded-md bg-white p-5 shadow-md'
								>
									<div className='h-7 w-3/4 rounded bg-base-100 animate-pulse' />
									<div className='mt-3 h-4 w-full rounded bg-base-100 animate-pulse' />
									<div className='mt-2 h-4 w-5/6 rounded bg-base-100 animate-pulse' />
									<div className='mt-auto flex items-center gap-3 pt-3 border-t border-base-100'>
										<div className='h-4 w-24 rounded bg-base-100 animate-pulse' />
										<div className='h-5 w-20 rounded-sm bg-base-100 animate-pulse' />
										<div className='ml-auto h-4 w-24 rounded bg-base-100 animate-pulse' />
									</div>
								</div>
							))}
						</>
					) : isViewCardOn ? (
						<>
							<Link
								href='/crear-proyecto'
								className='w-96 h-40 px-5 mx-auto my-1 pt-7 pb-5 bg-base-50 rounded-md shadow-[0px_4px_8px_0px_rgba(0,0,0,0.20)] outline-1 outline-black inline-flex flex-col justify-start items-start gap-4 overflow-hidden transition-all hover:shadow-lg hover:-translate-y-0.5'
							>
								<div className='self-stretch flex flex-col justify-start items-start gap-3.5'>
									<div className='self-stretch inline-flex justify-center items-center gap-16'>
										<Plus color='text-base-600' />
									</div>
									<div className='self-stretch h-8 relative'>
										<div className='left-11.25 top-[-0.35px] absolute justify-start text-black text-2xl font-semibold'>
											Crear nuevo proyecto
										</div>
									</div>
									<div className='self-stretch inline-flex justify-center items-center gap-2.5'>
										<div className='justify-start text-base-600 text-base font-normal'>
											Crea algo innovador
										</div>
									</div>
								</div>
							</Link>

							{projects.map((project) => (
								<article
									key={project.id}
									onClick={() => handleProjectClick(project)}
									className='flex h-40 w-96 mx-auto my-1 cursor-pointer flex-col rounded-md bg-white p-5 shadow-md transition-all hover:shadow-lg hover:-translate-y-0.5'
								>
									<header>
										<h3 className='truncate text-2xl font-semibold text-black capitalize'>
											{project.name}
										</h3>
									</header>

									<p className='mt-2 line-clamp-2 text-base text-base-600 capitalize'>
										{project.description || 'Sin descripción'}
									</p>

									<div className='flex items-center gap-3 pt-3 border-t border-base-100'>
										<div className='flex items-center gap-1.5'>
											<Clock size={14} color='text-base-600' />
											<span className='text-sm text-base-600'>
												{new Date(project.created_at).toLocaleDateString()}
											</span>
										</div>
										{project.current_phase && (
											<span className='text-xs text-base-600 bg-base-100 px-2 py-0.5 rounded-sm'>
												{project.current_phase}
											</span>
										)}
										<div className='ml-auto flex items-center gap-1.5'>
											<div className='w-2 h-2 rounded-full bg-primary-100' />
											<span className='text-xs text-primary-100 font-medium'>
												{project.status || 'En progreso'}
											</span>
										</div>
									</div>
								</article>
							))}
						</>
					) : (
						<>
							<table className='w-full flex-1 px-4'>
								<thead className='sticky top-0 z-10 bg-base-100'>
									<tr className='bg-base-100 border-b border-base-200'>
										<th className='px-4 py-3 text-left text-base-600 text-lg font-semibold'>
											Proyecto
										</th>
										<th className='w-44 px-4 py-3 text-left text-base-600 text-lg font-semibold'>
											Fase Actual
										</th>
										<th className='w-44 px-4 py-3 text-center text-base-600 text-lg font-semibold'>
											Estado
										</th>
										<th className='w-44 px-4 py-3 text-right text-base-600 text-lg font-semibold'>
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

									{projects.map((project, index) => (
										<tr
											key={project.id}
											onClick={() => handleProjectClick(project)}
											className={`cursor-pointer border-b border-base-100 transition-colors hover:bg-primary-50/50 ${
												index % 2 === 0 ? 'bg-white' : 'bg-base-50'
											}`}
										>
											<td className='p-3'>
												<div className='flex flex-col gap-1.5'>
													<h3 className='text-base-950 text-base font-medium truncate capitalize'>
														{project.name}
													</h3>
													<p className='text-base-600 text-sm capitalize'>
														{project.description || 'Sin descripción'}
													</p>
												</div>
											</td>

											<td className='w-44 p-3 text-base-600 text-base capitalize'>
												{project.current_phase || 'Descubrimiento'}
											</td>

											<td className='w-44 p-3'>
												<div className='flex justify-center'>
													<div className='p-1 px-3 bg-primary-50 rounded-sm flex items-center gap-2.5'>
														<Clock size={16} color='text-primary-100' />
														<span className='text-primary-100 text-sm font-medium'>
															{project.status || 'En progreso'}
														</span>
													</div>
												</div>
											</td>

											<td className='w-44 p-3 text-right text-base-600 text-sm'>
												<time dateTime={project.created_at}>
													{new Date(project.created_at).toLocaleDateString()}
												</time>
											</td>
										</tr>
									))}
								</tbody>

								<tfoot className='sticky bottom-0 bg-base-100 border-t border-base-200'>
									<tr>
										<td colSpan={4} className='px-4 text-left'>
											<Link
												href='/crear-proyecto'
												className='p-3 inline-flex items-center gap-3'
											>
												<div className='p-1 rounded-sm outline outline-base-600'>
													<Plus color='text-base-600' />
												</div>
												<span className='text-base-950 text-xl'>
													Crear nuevo proyecto
												</span>
											</Link>
										</td>
									</tr>
								</tfoot>
							</table>
						</>
					)}
				</div>
			</div>
		</section>
	);
}
