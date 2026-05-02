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
	project: {
		name: string;
	};
	phases?: ProjectPhase[];
	provider: string;
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
	project,
	phases,
	provider,
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
		<header className='sticky top-0 z-40 flex h-(--topbar-h) shrink-0 items-center gap-3 border-b border-border-default bg-bg-base px-3.5 shadow-sm'>
			<button
				className='btn btn-ghost h-7 px-2 text-xs gap-1.5'
				onClick={handleBackToHub}
			>
				<span aria-hidden='true'>←</span>
				Kosmo
			</button>

			<span className='text-base text-border-default' aria-hidden='true'>
				|
			</span>

			<button
				type='button'
				className='btn btn-ghost h-7 px-2 text-xs font-semibold text-text-primary hover:text-text-primary'
				onClick={() => setAvatarOpen(false)}
			>
				{project.name}
			</button>

			<nav className='mx-2 hidden flex-1 items-center justify-center gap-1 md:flex'>
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

			<div className='flex items-center gap-2'>
				<span className='chip hidden bg-bg-subtle text-text-secondary sm:inline-flex'>
					{provider}
				</span>

				<button
					className='btn btn-secondary h-7 px-2.5 text-xs gap-1.5'
					onClick={handleOpenPalette}
				>
					<span aria-hidden='true'>⌘</span>
					Ctrl+K
				</button>

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
							<DropdownItem
								icon='key'
								label='Bóveda de API Keys'
								onClick={handleOpenApiKeys}
							/>
							<DropdownItem
								icon='settings'
								label='Configuración'
								onClick={() => setAvatarOpen(false)}
							/>
							<DropdownItem
								icon='log-out'
								label='Cerrar sesión'
								onClick={() => setAvatarOpen(false)}
							/>
						</div>
					)}
				</div>
			</div>
		</header>
	);
}

interface DropdownItemProps {
	icon: string;
	label: string;
	onClick: () => void;
}

function DropdownItem({ icon, label, onClick }: DropdownItemProps) {
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
			{/* <Icon name={icon} size={13} color='var(--text-secondary)' /> */}
			{label}
		</button>
	);
}
