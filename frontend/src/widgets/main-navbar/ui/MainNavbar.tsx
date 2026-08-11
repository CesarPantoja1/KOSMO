'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAppStore } from 'app/store/app.store';

import { Project, useProjectStore } from '@/entities/project';
import { WizardNavegacion } from '@/widgets/wizard-navegacion/ui/WizardNavegacion';
import { ComputerDesktop, Home, Sidebar, UserCircle } from './icons';

interface MainNavbarProps {
	children: React.ReactNode;
}

export function MainNavbar({ children }: MainNavbarProps) {
	const projects = useProjectStore((s) => s.projects);
	const getProjectsStore = useProjectStore((s) => s.getProjects);

	const [avatarOpen, setAvatarOpen] = useState(false);
	const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);
	const router = useRouter();

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				await getProjectsStore();
			} catch (error) {
				console.error('Failed to load projects', error);
			}
		};
		fetchProjects();
	}, [getProjectsStore]);

	const currentProject = useProjectStore((s) => s.currentProject);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);

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
		useAppStore.getState().resetStateBeforeChangeProject();
		useProjectStore.getState().setProjectState(project);
		router.push('/proyecto/descubrimiento');
	};

	return (
		<header className='flex h-screen max-h-screen overflow-hidden transition-all duration-300'>
			{!isEditorMaximized && (
				<div
					className={`flex max-h-screen flex-col bg-neutral-900 transition-all duration-300 shrink-0 ${isSidebarExpanded ? 'w-64' : 'w-13'}`}
				>
					{/* Logo / Brand */}
					<div className='relative group flex min-h-16 items-center justify-center border-b border-neutral-700'>
						{isSidebarExpanded ? (
							<>
								<button
									className='text-xl font-bold text-neutral-0 cursor-pointer whitespace-nowrap tracking-wide'
									onClick={handleBackToHub}
								>
									KOSMO
								</button>
								<button
									className='absolute top-0 bottom-0 right-3 flex items-center justify-center cursor-pointer text-neutral-400 hover:text-neutral-0 transition-colors'
									onClick={() => setIsSidebarExpanded(false)}
								>
									<Sidebar size={22} color='text-current' />
								</button>
							</>
						) : (
							<>
								<span className='text-xl font-bold text-neutral-0 select-none group-hover:invisible'>
									K
								</span>
								<button
									className='absolute top-0 bottom-0 flex items-center justify-center cursor-pointer text-neutral-400 hover:text-neutral-0 transition-colors opacity-0 group-hover:opacity-100'
									onClick={() => setIsSidebarExpanded(true)}
								>
									<Sidebar size={22} color='text-current' />
								</button>
							</>
						)}
					</div>

					{/* Project list */}
					<div className='flex flex-col flex-1 py-3 px-1 overflow-y-auto'>
						{isSidebarExpanded ? (
							<div className='flex flex-col gap-1'>
								<button
									className='flex items-center px-3 py-2.5 gap-2.5 cursor-pointer rounded-md transition-colors text-neutral-300 hover:bg-neutral-800 hover:text-neutral-0 border-l-2 border-transparent'
									onClick={() => router.push('/')}
									title='Inicio'
								>
									<Home size={20} color='text-neutral-500' />
									<span className='flex-1 text-left truncate font-medium'>Inicio</span>
								</button>
								<span className='text-neutral-500 text-xs font-semibold uppercase tracking-wider px-3 pb-2 pt-1'>
									Proyectos
								</span>
								{projects.map((project) => {
									const isActive = currentProject?.id === project.id;
									return (
										<button
											key={project.id}
											type='button'
											className={`flex items-center px-3 py-2.5 gap-2.5 cursor-pointer rounded-md transition-colors text-left ${
												isActive
													? 'bg-neutral-700 text-neutral-0 border-l-2 border-primary-500'
													: 'text-neutral-300 hover:bg-neutral-800 hover:text-neutral-0 border-l-2 border-transparent'
											}`}
											onClick={() => handleProjectClick(project)}
											title={project.name}
										>
											<ComputerDesktop
												size={20}
												color={isActive ? 'text-primary-500' : 'text-neutral-500'}
											/>
											<span className='flex-1 text-left truncate font-medium capitalize'>
												{project.name}
											</span>
										</button>
									);
								})}
							</div>
						) : (
							<div className='flex flex-col gap-1 items-center'>
								<button
									className='flex items-center justify-center w-10 h-10 cursor-pointer rounded-md transition-colors text-neutral-400 hover:bg-neutral-800 hover:text-neutral-0'
									onClick={() => router.push('/')}
									title='Inicio'
								>
									<Home size={20} color='text-current' />
								</button>
								{projects.map((project) => {
									const isActive = currentProject?.id === project.id;
									return (
										<button
											key={project.id}
											type='button'
											className={`flex items-center justify-center w-10 h-10 cursor-pointer rounded-md transition-colors ${
												isActive
													? 'bg-neutral-700 text-neutral-0'
													: 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-0'
											}`}
											onClick={() => handleProjectClick(project)}
											title={project.name}
										>
											<span className='text-sm font-semibold'>
												{project.name.slice(0, 2).toUpperCase()}
											</span>
										</button>
									);
								})}
							</div>
						)}
					</div>

					{/* User section */}
					<div
						className={`border-t border-neutral-700 inline-flex items-center gap-3 overflow-hidden mt-auto ${
							isSidebarExpanded ? 'px-3 py-4 justify-start' : 'p-2 py-4 justify-center'
						}`}
					>
						<UserCircle size={36} color='text-neutral-400' className='shrink-0' />
						{isSidebarExpanded && (
							<div className='flex-1 min-w-0 flex flex-col justify-center'>
								<h4 className='text-neutral-0 text-sm font-semibold truncate'>
									Carlos Yupa
								</h4>
								<button className='text-left text-neutral-500 text-xs font-normal hover:text-neutral-300 transition-colors'>
									Cerrar sesión
								</button>
							</div>
						)}
					</div>
				</div>
			)}

			<main
				className={`flex flex-1 min-h-0 flex-col overflow-hidden transition-all duration-300 ${isEditorMaximized ? '' : 'mx-8'}`}
			>
				{!isEditorMaximized && (
					<div className='z-50 shrink-0'>
						<WizardNavegacion />
					</div>
				)}
				<section className='min-h-0 flex-1 overflow-hidden'>{children}</section>
			</main>
		</header>
	);
}
