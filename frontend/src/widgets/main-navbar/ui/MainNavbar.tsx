'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, usePathname, useRouter } from 'next/navigation';

type ProjectPhase = {
	key: string;
	label: string;
	href?: string;
};

interface MainNavbarProps {
	children: React.ReactNode;
	project: {
		name: string;
	};
	phases?: ProjectPhase[];
	onBackToHub?: () => void;
	onOpenPalette?: () => void;
	onOpenApiKeys?: () => void;
}

const defaultPhases: ProjectPhase[] = [
	{ key: 'requirements', label: 'Requirements' },
	{ key: 'discovery', label: 'Discovery' },
	{ key: 'idea', label: 'Idea' },
	{ key: 'modeling', label: 'Modeling' },
];

export function MainNavbar({
	children,
	project,
	phases,
	onBackToHub,
	onOpenPalette,
	onOpenApiKeys,
}: MainNavbarProps) {
	const [avatarOpen, setAvatarOpen] = useState(false);
	const router = useRouter();
	const pathname = usePathname();
	const params = useParams<{ projectId?: string }>() ?? {};
	const projectId = typeof params.projectId === 'string' ? params.projectId : undefined;
	const projectPhases = phases?.length ? phases : defaultPhases;

	const handleBackToHub = () => {
		setAvatarOpen(false);
		if (onBackToHub) {
			onBackToHub();
			return;
		}

		router.push('/');
	};

	const handleOpenPalette = () => {
		if (onOpenPalette) {
			onOpenPalette();
		}
	};

	const handleOpenApiKeys = () => {
		setAvatarOpen(false);
		if (onOpenApiKeys) {
			onOpenApiKeys();
			return;
		}

		router.push('/profile');
	};

	const getPhaseHref = (phase: ProjectPhase) => {
		if (phase.href) {
			return phase.href;
		}

		if (!projectId) {
			return '/';
		}

		return `/project/${projectId}/${phase.key}`;
	};

	const isPhaseActive = (phase: ProjectPhase) => {
		const href = getPhaseHref(phase);
		return pathname === href || pathname?.endsWith(`/${phase.key}`);
	};

	return (
		<header className='flex h-screen max-h-screen'>
			<div className='flex-2/12 max-h-screen p-4 bg-green-700'>
				<div className='flex flex-col '>
					<span>KOSMO</span>
					<button className='text-base' onClick={handleBackToHub}>
						HOME
					</button>
					<hr />
					<div className='flex justify-between gap-2'>
						<h2>Proyectos</h2>
						<button>+</button>
					</div>
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
						{project.name}
					</button>
				</div>

				<div className='flex items-center gap-2'>
					<span className='chip hidden bg-bg-subtle text-text-secondary sm:inline-flex'></span>

					<div className='relative'>
						<button
							type='button'
							className='flex h-7 w-7 items-center justify-center rounded-full border-2 border-accent-primary bg-blue-50 text-[11px] font-bold text-accent-primary shadow-sm transition hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/50'
							onClick={() => setAvatarOpen((value) => !value)}
							aria-haspopup='menu'
							aria-expanded={avatarOpen}
						>
							M
						</button>

						{avatarOpen && (
							<div className='anim-fade-in absolute right-0 top-[120%] z-50 min-w-44 overflow-hidden rounded-md border border-border-default bg-bg-base shadow-lg'>
								<DropdownItem label='Bóveda de API Keys' onClick={handleOpenApiKeys} />
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

			<div className='flex-10/12 max-h-screen relative overflow-y-auto p-4 bg-red-400'>
				<div className='sticky top-0 left-0 max-h-screen '>
					<div className='flex items-center gap-2 p-2'>HOla</div>
					<nav className='mx-2 flex-1 items-center justify-center gap-1 bg-indigo-400'>
						{projectPhases.map((phase) => {
							const href = getPhaseHref(phase);
							const active = isPhaseActive(phase);

							return (
								<Link
									key={phase.key}
									href={href}
									className={`btn h-8 px-3 text-xs transition-colors ${
										active
											? 'bg-bg-subtle text-text-primary border-border-strong'
											: 'btn-ghost text-text-secondary'
									}`}
									aria-current={active ? 'page' : undefined}
								>
									{phase.label}
								</Link>
							);
						})}
					</nav>
				</div>
				<main>{children}</main>
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
