'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAppStore } from 'app/store/app.store';

import { getStyleIconStatus } from '../lib/get-status-color';
import { ProjectStatus } from '../types/status';
import WizardItem from './WizardItem';
import {
	Characteristics,
	ComputerDesktop,
	Home,
	Implementation,
	Modeling,
	Requirements,
	Right,
	Sidebar,
	UserCircle,
} from './icons';
import Discovery from './icons/Discovery';

interface MainNavbarProps {
	children: React.ReactNode;
}

export function MainNavbar({ children }: MainNavbarProps) {
	const [avatarOpen, setAvatarOpen] = useState(false);
	const router = useRouter();
	const pathname = usePathname();

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
					<div className='absolute right-1 top-0 bottom-0 flex items-center justify-center'>
						<Sidebar size={38} color='text-base-50' />
					</div>
				</div>
				<hr />
				<div className='flex justify-between gap-2'>
					<h2>Proyectos</h2>
					<Link
						className='flex h-12 w-full items-center justify-center rounded-full border border-solid border-black/[.08] px-5 transition-colors hover:border-transparent hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-[#1a1a1a] md:w-[158px]'
						href='/crear-proyecto'
						rel='noopener noreferrer'
					>
						+
					</Link>
				</div>

				<div className='flex flex-col align-top flex-1'>
					<span className='text-base text-border-default' aria-hidden='true'>
						Recientes
					</span>

					<button
						type='button'
						className='btn btn-ghost h-7 px-2 text-xs font-semibold text-text-primary hover:text-text-primary'
						onClick={() => setAvatarOpen(false)}
					>
						<ComputerDesktop color='text-base-600' /> {currentProject?.name}
					</button>
				</div>

				<div className='flex items-center gap-2'>
					<span className='chip hidden bg-bg-subtle text-text-secondary sm:inline-flex'></span>

					<div className='relative'>
						<button
							type='button'
							className='flex items-center justify-center rounded-full border'
							onClick={() => setAvatarOpen((value) => !value)}
							aria-haspopup='menu'
							aria-expanded={avatarOpen}
						>
							<UserCircle color='text-base-600' />
						</button>

						{avatarOpen && (
							<div className='anim-fade-in absolute right-0 top-[120%] z-50 min-w-44 overflow-hidden rounded-md border border-border-default bg-bg-base shadow-lg'>
								<DropdownItem
									label='Bóveda de API Keys'
									onClick={() => setAvatarOpen(false)}
								/>
								<DropdownItem
									label='Configuración'
									onClick={() => setAvatarOpen(false)}
								/>
								<DropdownItem
									label='Cerrar sesión'
									onClick={() => setAvatarOpen(false)}
								/>
							</div>
						)}
					</div>
				</div>
			</div>

			<div className='flex w-10/12 min-h-0 flex-col overflow-hidden mx-8'>
				<div className='z-50 shrink-0'>
					<div className='flex items-center gap-1 py-3'>
						<Home size={32} color='text-base-600' />
						<Right size={28} color='text-base-600' />
						<span className='text-base-600 text-xl font-medium'>Descripción</span>
					</div>

					{isProyectosOpen && (
						<nav className='flex justify-between px-16 py-3 mx-0.5 bg-base-50 outline outline-base-300 rounded-sm'>
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
				<main className='min-h-0 flex-1 overflow-hidden'>{children}</main>
			</div>
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
