'use client';

import { getProjects } from '@/entities/project/api/api';
import { Project } from '@/entities/project/model/types';
import { Plus } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Cards, Clock, List } from './icons';

const stylesButtonToggle = {
	on: {
		button: 'bg-primary-500 border-primary-600 shadow-sm',
		icon: 'text-neutral-0',
	},
	off: {
		button: 'bg-neutral-0 border border-neutral-300 hover:bg-neutral-100',
		icon: 'text-neutral-500',
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
				{/* Header row: title + actions */}
				<div className='flex items-start justify-between gap-4'>
					<div className='flex flex-col gap-1'>
						<h2 className='text-neutral-800 text-3xl font-bold'>Proyectos</h2>
						<p className='text-neutral-500 text-base'>
							Gestiona y da seguimiento a tus iniciativas de producto
						</p>
					</div>

					<div className='flex items-center gap-3 shrink-0'>
						{/* View toggles */}
						<div className='flex rounded-md overflow-hidden border border-neutral-300'>
							<button
								onClick={setViewCard}
								className={`px-3 py-2 cursor-pointer transition-all duration-200 ease-in-out ${stylesToogleView.card.button}`}
								title='Vista de tarjetas'
							>
								<Cards size={18} color={stylesToogleView.card.icon} />
							</button>
							<button
								onClick={setViewList}
								className={`px-3 py-2 cursor-pointer transition-all duration-200 ease-in-out border-l border-neutral-300 ${stylesToogleView.list.button}`}
								title='Vista de lista'
							>
								<List size={18} color={stylesToogleView.list.icon} />
							</button>
						</div>

						{/* Primary CTA */}
						<Link href='/crear-proyecto' className='btn btn-primary'>
							<Plus color='text-neutral-0' />
							<span>Nuevo proyecto</span>
						</Link>
					</div>
				</div>

				{/* Content area */}
				<div className='pb-8 overflow-y-auto relative'>
					{loading ? (
						/* Skeleton grid */
						<div className='grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5'>
							{Array.from({ length: 6 }).map((_, index) => (
								<div
									key={index}
									className='flex min-h-40 flex-col rounded-lg bg-neutral-0 p-5 shadow-sm border border-neutral-200'
								>
									<div className='h-6 w-3/4 rounded-md bg-neutral-100 animate-pulse' />
									<div className='mt-3 h-4 w-full rounded-md bg-neutral-100 animate-pulse' />
									<div className='mt-2 h-4 w-5/6 rounded-md bg-neutral-100 animate-pulse' />
									<div className='mt-auto flex items-center gap-3 pt-3 border-t border-neutral-100'>
										<div className='h-4 w-24 rounded-md bg-neutral-100 animate-pulse' />
										<div className='ml-auto h-5 w-20 rounded-md bg-neutral-100 animate-pulse' />
									</div>
								</div>
							))}
						</div>
					) : isViewCardOn ? (
						/* Card grid */
						<div className='grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5 max-w-[1800px]'>
							{/* Create new card */}
							<Link
								href='/crear-proyecto'
								className='flex min-h-40 flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-neutral-300 bg-neutral-50 p-5 transition-all hover:border-primary-500 hover:bg-primary-50 hover:shadow-md group'
							>
								<div className='flex h-10 w-10 items-center justify-center rounded-full bg-neutral-200 group-hover:bg-primary-100 transition-colors'>
									<Plus color='text-neutral-500 group-hover:text-primary-600' />
								</div>
								<div className='text-center'>
									<p className='text-neutral-700 font-semibold group-hover:text-primary-600 transition-colors'>
										Crear nuevo proyecto
									</p>
									<p className='text-neutral-400 text-sm mt-0.5'>
										Comienza una nueva iniciativa
									</p>
								</div>
							</Link>

							{/* Project cards */}
							{projects.map((project) => (
								<article
									key={project.id}
									onClick={() => handleProjectClick(project)}
									className='flex min-h-40 cursor-pointer flex-col rounded-lg bg-neutral-0 p-5 shadow-sm border border-neutral-200 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-neutral-300'
								>
									<header>
										<h3 className='truncate text-lg font-semibold text-neutral-800 capitalize'>
											{project.name}
										</h3>
									</header>

									<p className='mt-2 line-clamp-2 text-sm text-neutral-500 capitalize flex-1'>
										{project.description || 'Sin descripción'}
									</p>

									<div className='flex items-center gap-3 pt-3 mt-3 border-t border-neutral-100'>
										<div className='flex items-center gap-1.5'>
											<Clock size={13} color='text-neutral-400' />
											<span className='text-xs text-neutral-400'>
												{new Date(project.created_at).toLocaleDateString()}
											</span>
										</div>
										{project.current_phase && (
											<span className='text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full'>
												{project.current_phase}
											</span>
										)}
										<div className='ml-auto flex items-center gap-1.5'>
											<div className='w-1.5 h-1.5 rounded-full bg-primary-500' />
											<span className='text-xs text-primary-500 font-medium'>
												{project.status || 'En progreso'}
											</span>
										</div>
									</div>
								</article>
							))}
						</div>
					) : (
						/* Table view */
						<table className='w-full flex-1'>
							<thead className='sticky top-0 z-10'>
								<tr className='bg-neutral-100 border-b border-neutral-200'>
									<th className='px-4 py-3 text-left text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
										Proyecto
									</th>
									<th className='w-44 px-4 py-3 text-left text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
										Fase Actual
									</th>
									<th className='w-44 px-4 py-3 text-center text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
										Estado
									</th>
									<th className='w-44 px-4 py-3 text-right text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
										Creado
									</th>
								</tr>
							</thead>

							<tbody>
								{projects.length === 0 && (
									<tr>
										<td
											colSpan={4}
											className='p-8 bg-neutral-0 text-center text-neutral-400 text-sm'
										>
											No tienes proyectos creados. Crea tu primer proyecto para comenzar.
										</td>
									</tr>
								)}

								{projects.map((project, index) => (
									<tr
										key={project.id}
										onClick={() => handleProjectClick(project)}
										className={`cursor-pointer border-b border-neutral-100 transition-colors hover:bg-primary-50 ${
											index % 2 === 0 ? 'bg-neutral-0' : 'bg-neutral-50'
										}`}
									>
										<td className='p-4'>
											<div className='flex flex-col gap-1'>
												<h3 className='text-neutral-800 text-sm font-semibold truncate capitalize'>
													{project.name}
												</h3>
												<p className='text-neutral-400 text-xs capitalize'>
													{project.description || 'Sin descripción'}
												</p>
											</div>
										</td>

										<td className='w-44 p-4 text-neutral-600 text-sm capitalize'>
											{project.current_phase || 'Descubrimiento'}
										</td>

										<td className='w-44 p-4'>
											<div className='flex justify-center'>
												<div className='px-3 py-1 bg-primary-50 border border-primary-100 rounded-full flex items-center gap-2'>
													<Clock size={13} color='text-primary-500' />
													<span className='text-primary-500 text-xs font-medium'>
														{project.status || 'En progreso'}
													</span>
												</div>
											</div>
										</td>

										<td className='w-44 p-4 text-right text-neutral-400 text-xs'>
											<time dateTime={project.created_at}>
												{new Date(project.created_at).toLocaleDateString()}
											</time>
										</td>
									</tr>
								))}
							</tbody>

							<tfoot className='sticky bottom-0 bg-neutral-100 border-t border-neutral-200'>
								<tr>
									<td colSpan={4} className='px-4 text-left'>
										<Link
											href='/crear-proyecto'
											className='py-3 inline-flex items-center gap-2 text-neutral-500 hover:text-primary-500 transition-colors'
										>
											<div className='flex h-7 w-7 items-center justify-center rounded-md border border-neutral-300 hover:border-primary-500 transition-colors'>
												<Plus color='text-current' />
											</div>
											<span className='text-sm font-medium'>Crear nuevo proyecto</span>
										</Link>
									</td>
								</tr>
							</tfoot>
						</table>
					)}
				</div>
			</div>
		</section>
	);
}
