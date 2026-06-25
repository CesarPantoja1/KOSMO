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

					<WizardNavegacion />
				</div>
				<section className='min-h-0 flex-1 overflow-hidden'>{children}</section>
			</main>
		</header>
	);
}

interface DropdownItemProps {
	label: string;
	onClick: () => void;
}

function DropdownItem({ label, onClick }: DropdownItemProps) {
	return (
		<button
			className='btn btn-ghost'
			type='button'
			style={{
				width: '100%',
				justifyContent: 'flex-start',
				borderRadius: 0,
				height: 32,
				padding: '0 12px',
				fontSize: 13,
				gap: 8,
			}}
			onClick={onClick}
		>
			{label}
		</button>
	);
}
