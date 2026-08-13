'use client';

import { Plus } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { Project, useProjectStore } from '@/entities/project';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Cards, List } from './icons';
import SkeletonCardProject from './SkeletonCardProject';
import ViewCardProject from './ViewCardProject';
import ViewTableProject from './ViewTableProject';

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
	const { setProjectState } = useProjectStore();
	const resetStateBeforeChangeProject = useAppStore(
		(s) => s.resetStateBeforeChangeProject,
	);
	const projects = useProjectStore((s) => s.projects);
	const getProjectsStore = useProjectStore((s) => s.getProjects);
	const [loading, setLoading] = useState(true);

	const [isViewCardOn, setIsViewCardOn] = useState(true);
	const [stylesToogleView, setStylesToogleView] = useState<viewStyles>({
		list: stylesButtonToggle.off,
		card: stylesButtonToggle.on,
	});

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				await getProjectsStore();
			} catch (error) {
				console.error('Failed to load projects', error);
			} finally {
				setLoading(false);
			}
		};
		resetStateBeforeChangeProject();
		fetchProjects();
	}, [resetStateBeforeChangeProject, getProjectsStore]);

	const initializeProject = useAppStore((s) => s.initializeProject);

	const handleProjectClick = (project: Project) => {
		resetStateBeforeChangeProject();
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
				<section className='pb-8 overflow-y-auto relative'>
					{loading ? (
						<SkeletonCardProject />
					) : isViewCardOn ? (
						<ViewCardProject
							projects={projects}
							handleProjectClick={handleProjectClick}
						/>
					) : (
						<ViewTableProject
							projects={projects}
							handleProjectClick={handleProjectClick}
						/>
					)}
				</section>
			</div>
		</section>
	);
}
