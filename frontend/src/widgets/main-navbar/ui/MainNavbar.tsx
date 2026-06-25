'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAppStore } from 'app/store/app.store';

import { WizardNavegacion } from '@/widgets/wizard-navegacion';
import {
	Characteristics,
	ComputerDesktop,
	Folder,
	Home,
	Implementation,
	Modeling,
	Requirements,
	Right,
	Sidebar,
	UserCircle,
} from './icons';
import Discovery from './icons/Discovery';
import { ArrowRight } from '@/shared/ui';
import { Project, projectsApi } from '@/entities/project';

interface MainNavbarProps {
	children: React.ReactNode;
}

export function MainNavbar({ children }: MainNavbarProps) {
	const { setProjectState } = useAppStore();
	const [projects, setProjects] = useState<Project[]>([]);

	const [avatarOpen, setAvatarOpen] = useState(false);
	const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);
	const router = useRouter();
	const pathname = usePathname();

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				const data = await projectsApi.getProjects();
				setProjects(data);
			} catch (error) {
				console.error('Failed to load projects', error);
			}
		};
		fetchProjects();
	}, []);

	const isProyectosOpen = useAppStore((s) => s.isProyectosOpen);
	const currentProject = useAppStore((s) => s.currentProject);


	const handleBackToHub = () => {
		setAvatarOpen(false);

		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			setPendingNavigationPath('/proyecto');
			return;
		}

		router.push('/proyecto');
	};



	const handleProjectClick = (project: Project) => {
		setProjectState(project);
		router.push('/proyecto/descubrimiento');
	};

	return (
		<header className='flex h-screen max-h-screen overflow-hidden transition-all duration-300'>
			<div className={`flex max-h-screen flex-col overflow-y-auto bg-base-200 transition-all duration-300 shrink-0 ${isSidebarExpanded ? 'w-2/12' : 'w-[80px]'}`}>
				<div className='relative flex min-h-[72px] items-center justify-center bg-primary-100'>
					{isSidebarExpanded && (
						<button
							className='text-2xl font-semibold text-base-50 cursor-pointer whitespace-nowrap'
							onClick={handleBackToHub}
						>
							KOSMO
						</button>
					)}
					<button 
						className={`absolute top-0 bottom-0 flex items-center justify-center cursor-pointer ${isSidebarExpanded ? 'right-2' : ''}`}
						onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
					>
						<Sidebar size={38} color='text-base-50' />
					</button>
				</div>
				
				{isSidebarExpanded ? (
					<h2 className='text-primary-100 text-2xl font-semibold p-2 border-b border-base-800 whitespace-nowrap'>
						Proyectos
					</h2>
				) : (
					<div className='border-b border-base-800 h-[49px]'></div>
				)}

				<div className='flex flex-col flex-1 p-2'>
					{/* Listar todos los proyectos */}
					{isSidebarExpanded ? (
						<div className='flex flex-col gap-2'>
							<span className='text-base-600 text-lg font-semibold px-2 pt-2'>Recientes</span>
							<button
								type='button'
								className='flex items-center px-3.5 py-2.5 gap-2 cursor-pointer bg-base-200 hover:bg-base-300 text-base-800 rounded-sm transition-colors'
								onClick={() => handleProjectClick(currentProject!)}
							>
								<ComputerDesktop color='text-base-600' />
								<span className='flex-1 text-left truncate text-base font-medium'>{currentProject?.name}</span>
							</button>
						</div>
					) : (
						<button
							type='button'
							className='flex items-center justify-center py-4 cursor-pointer text-base-800'
							onClick={() => handleProjectClick(currentProject!)}
							title={currentProject?.name}
						>
							<Folder size={32} color='text-base-600' />
						</button>
					)}
				</div>

				<div className={`border-t border-base-600 inline-flex items-center gap-3 overflow-hidden ${isSidebarExpanded ? 'pl-2 pt-8 pb-4 justify-start' : 'p-2 py-8 justify-center'}`}>
					<UserCircle size={40} color='text-base-600' className='shrink-0' />
					{isSidebarExpanded && (
						<div className='w-40 inline-flex flex-col justify-center items-start'>
							<h4 className="justify-start text-base-800 text-2xl font-semibold font-['Geist'] truncate w-full text-left">
								Carlos Yupa
							</h4>
							<button className="justify-start text-base-600 text-base font-normal font-['Geist']">
								Salir
							</button>
						</div>
					)}
				</div>
			</div>

			<main className='flex flex-1 min-h-0 flex-col overflow-hidden mx-8 transition-all duration-300'>
				<div className='z-50 shrink-0'>
					<div className='flex items-center gap-1 py-2'>
						<Home size={20} color='text-base-600' />
						<Right size={16} color='text-base-600' />
						<span className='text-base-600 text-sm font-medium capitalize'>
							{pathname.split('/').pop()}
						</span>
					</div>

					<WizardNavegacion />
				</div>
				<section className='min-h-0 flex-1 overflow-hidden'>{children}</section>
			</main>
		</header>
	);
}
