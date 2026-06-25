'use client';

import { usePathname } from 'next/navigation';
import { useAppStore } from 'app/store/app.store';

import { getStyleIconStatus } from '../lib/get-status-color';
import { ProjectStatus } from '../types/status';
import WizardItem from './WizardItem';

import Discovery from '@/widgets/main-navbar/ui/icons/Discovery';
import { Characteristics, Requirements, Modeling, Implementation } from '@/widgets/main-navbar/ui/icons';

const phaseItems = [
	{ href: '/proyecto/descubrimiento', Icon: Discovery, label: 'Descubrimiento' },
	{ href: '/proyecto/caracteristicas', Icon: Characteristics, label: 'Características' },
	{ href: '/proyecto/requisitos', Icon: Requirements, label: 'Requisitos' },
	{ href: '/proyecto/modelo', Icon: Modeling, label: 'Modelo' },
	{ href: '/proyecto/codigo', Icon: Implementation, label: 'Código' },
] as const;

export function WizardNavegacion() {
	const pathname = usePathname();
	const isProyectosOpen = useAppStore((s) => s.isProyectosOpen);

	const handleWizardClick = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			e.preventDefault();
			setPendingNavigationPath(href);
		}
	};

	if (!isProyectosOpen) return null;

	return (
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
	);
}
