'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAppStore } from 'app/store/app.store';

import { getStyleIconStatus } from '../lib/get-status-color';
import { ProjectStatus } from '../types/status';
import WizardItem from './WizardItem';
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

	const phaseItems = [
		{ href: '/proyecto/descubrimiento', Icon: Discovery, label: 'Descubrimiento' },
		{
			href: '/proyecto/caracteristicas',
			Icon: Characteristics,
			label: 'Características',
		},
		{ href: '/proyecto/requisitos', Icon: Requirements, label: 'Requisitos' },
		{ href: '/proyecto/modelo', Icon: Modeling, label: 'Modelo' },
		{ href: '/proyecto/codigo', Icon: Implementation, label: 'Código' },
	] as const;

	const handleBackToHub = () => {
		setAvatarOpen(false);

		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			setPendingNavigationPath('/proyecto');
			return;
		}

		router.push('/proyecto');
	};

	const handleWizardClick = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			e.preventDefault();
			setPendingNavigationPath(href);
		}
	};

	const handleProjectClick = (project: Project) => {
		setProjectState(project);
		router.push('/proyecto/descubrimiento');
	};

	return (
		<header className='flex h-screen max-h-screen overflow-hidden'>
			<div className='flex w-2/12 max-h-screen flex-col overflow-y-auto bg-base-200'>
				<div className='relative flex py-5 justify-center bg-primary-100'>
					<button
						className='text-2xl font-semibold text-base-50 cursor-pointer'
						onClick={handleBackToHub}
					>
						KOSMO
					</button>
					<button className='absolute right-1 top-0 bottom-0 flex items-center justify-center'>
						<Sidebar size={38} color='text-base-50' />
					</button>
				</div>
				<h2 className='text-primary-100 text-2xl font-semibold p-2 border-b border-base-800'>
					Proyectos
				</h2>

				<div className='flex flex-col flex-1 p-2'>
					{/* Listar todos los proyectos */}
					<Folder
						size={32}
						color='text-primary-100 absolute left-1 top-0 bottom-0 m-auto'
					/>
					<button
						type='button'
						className='flex items-center px-3.5 py-2.5 gap-2 cursor-pointer bg-base-300 text-base-800'
						onClick={() => handleProjectClick(currentProject!)}
					>
						<ComputerDesktop color='text-base-600' />
						<span className='flex-1 text-left'>{currentProject?.name}</span>
						<Right size={24} color='text-base-600' />
					</button>
				</div>

				<div className='pl-2 pt-8 border-t border-base-600 inline-flex justify-start items-start gap-3'>
					<UserCircle size={40} color='text-base-600' />
					<div className='w-40 pb-2 inline-flex flex-col justify-center items-start'>
						<h4 className="justify-start text-base-800 text-2xl font-semibold font-['Geist']">
							Carlos Yupa
						</h4>
						<button className="justify-start text-base-600 text-base font-normal font-['Geist']">
							Salir
						</button>
					</div>
				</div>
			</div>

			<main className='flex w-10/12 min-h-0 flex-col overflow-hidden mx-8'>
				<div className='z-50 shrink-0'>
					<div className='flex items-center gap-1 py-3'>
						<Home size={32} color='text-base-600' />
						<Right size={28} color='text-base-600' />
						<span className='text-base-600 text-xl font-medium'>Descripción</span>
					</div>

					{isProyectosOpen && (
						<nav className='flex justify-between px-16 py-3 mx-0.5 mt-3 bg-base-50 outline outline-base-300 rounded-sm'>
							{phaseItems.map(({ href, Icon, label }) => {
								const status: ProjectStatus = pathname === href ? 'active' : 'disable';
								const colors = getStyleIconStatus(status);
								return (
									<WizardItem
										key={href}
										href={href}
										icon={<Icon color={colors.iconStyles} />}
										iconContainerStyles={colors.iconContainer}
										label={label}
										labelStyles={colors.labelStyles}
										onClick={handleWizardClick(href)}
									/>
								);
							})}
						</nav>
					)}
				</div>
				<section className='min-h-0 flex-1 overflow-hidden'>{children}</section>
			</main>
		</header>
	);
}
