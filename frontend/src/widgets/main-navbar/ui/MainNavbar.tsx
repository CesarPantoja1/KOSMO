'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAppStore } from 'app/store/app.store';

import { Project, getProjects } from '@/entities/project';
import { WizardNavegacion } from '@/widgets/wizard-navegacion/ui/WizardNavegacion';
import { ComputerDesktop, Sidebar, UserCircle } from './icons';

interface MainNavbarProps {
	children: React.ReactNode;
}

export function MainNavbar({ children }: MainNavbarProps) {
	const [projects, setProjects] = useState<Project[]>([]);

	const [avatarOpen, setAvatarOpen] = useState(false);
	const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);
	const router = useRouter();

	useEffect(() => {
		const fetchProjects = async () => {
			try {
				const data = await getProjects();
				setProjects(data);
			} catch (error) {
				console.error('Failed to load projects', error);
			}
		};
		fetchProjects();
	}, []);

	const currentProject = useAppStore((s) => s.currentProject);
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
		const { resetProjectState, setProjectState } = useAppStore.getState();
		resetProjectState();
		setProjectState(project);
		router.push('/proyecto/descubrimiento');
	};

	return (
		<header className='flex h-screen max-h-screen overflow-hidden transition-all duration-300'>
			{!isEditorMaximized && (
				<div
					className={`flex max-h-screen flex-col bg-base-200 transition-all duration-300 shrink-0 ${isSidebarExpanded ? 'w-2/12' : 'w-20'}`}
				>
					<div className='relative group flex min-h-18 items-center justify-center bg-primary-100'>
						{isSidebarExpanded ? (
							<>
								<button
									className='text-2xl font-semibold text-base-50 cursor-pointer whitespace-nowrap'
									onClick={handleBackToHub}
								>
									KOSMO
								</button>
								<button
									className='absolute top-0 bottom-0 right-2 flex items-center justify-center cursor-pointer'
									onClick={() => setIsSidebarExpanded(false)}
								>
									<Sidebar size={38} color='text-base-50' />
								</button>
							</>
						) : (
							<>
								<span className='text-2xl font-semibold text-base-50 select-none group-hover:invisible'>
									K
								</span>
								<button
									className='absolute top-0 bottom-0 flex items-center justify-center cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity'
									onClick={() => setIsSidebarExpanded(true)}
								>
									<Sidebar size={38} color='text-base-50' />
								</button>
							</>
						)}
					</div>

					<div className='flex flex-col flex-1 p-2 overflow-y-auto'>
						{isSidebarExpanded ? (
							<div className='flex flex-col gap-2'>
								<span className='text-base-600 text-lg font-semibold px-2 pt-2'>
									Proyectos
								</span>
								{projects.map((project) => {
									const isActive = currentProject?.id === project.id;
									return (
										<button
											key={project.id}
											type='button'
											className={`flex items-center px-3.5 py-2.5 gap-2 cursor-pointer rounded-sm transition-colors ${isActive ? 'bg-primary-100 text-primary-800' : 'bg-base-200 hover:bg-base-300 text-base-800'}`}
											onClick={() => handleProjectClick(project)}
											title={project.name}
										>
											<ComputerDesktop
												color={isActive ? 'text-primary-600' : 'text-base-600'}
											/>
											<span className='flex-1 text-left truncate text-base font-medium capitalize'>
												{project.name}
											</span>
										</button>
									);
								})}
							</div>
						) : (
							<div className='flex flex-col gap-2 items-center'>
								{projects.map((project) => {
									const isActive = currentProject?.id === project.id;
									return (
										<button
											key={project.id}
											type='button'
											className={`flex items-center justify-center w-12 h-12 cursor-pointer rounded-sm transition-colors ${isActive ? 'bg-primary-100 text-primary-800' : 'text-base-800 hover:bg-base-300'}`}
											onClick={() => handleProjectClick(project)}
											title={project.name}
										>
											<span
												className={`text-xl font-semibold ${isActive ? 'text-primary-600' : 'text-base-600'}`}
											>
												{project.name.charAt(0).toUpperCase()}
											</span>
										</button>
									);
								})}
							</div>
						)}
					</div>

					<div
						className={`border-t border-base-600 inline-flex items-center gap-3 overflow-hidden mt-auto ${isSidebarExpanded ? 'pl-2 pt-8 pb-4 justify-start' : 'p-2 py-8 justify-center'}`}
					>
						<UserCircle size={40} color='text-base-600' className='shrink-0' />
						{isSidebarExpanded && (
							<div className='w-40 inline-flex flex-col justify-center items-start'>
								<h4 className='justify-start text-base-800 text-2xl font-semibold truncate w-full text-left'>
									Carlos Yupa
								</h4>
								<button className='justify-start text-base-600 text-base font-normal'>
									Salir
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
						{/* <div className='flex items-center gap-1 py-2'>
							<Home size={40} color='text-base-600' />
							<Right size={36} color='text-base-600' />
							<span className='text-base-600 text-sm font-medium capitalize'>
								{pathname?.split('/').pop() || ''}
							</span> 
						</div> */}

						<WizardNavegacion />
						{/* <UserCircle size={40} color='text-base-600' /> */}
					</div>
				)}
				<section className='min-h-0 flex-1 overflow-hidden'>{children}</section>
			</main>
		</header>
	);
}
