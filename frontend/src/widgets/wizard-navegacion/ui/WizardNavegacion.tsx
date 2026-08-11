'use client';

import { usePathname } from 'next/navigation';
import { useAppStore } from 'app/store/app.store';
import { useProjectStore } from '@/entities/project';

import { getStyleIconStatus } from '../lib/get-status-color';
import { ProjectStatus } from '../types/status';
import WizardItem from './WizardItem';

import Discovery from '@/widgets/main-navbar/ui/icons/Discovery';
import {
	Characteristics,
	Requirements,
	Modeling,
	Implementation,
} from '@/widgets/main-navbar/ui/icons';

const phaseItems = [
	{ href: '/proyecto/descubrimiento', Icon: Discovery, label: 'DESCUBRIMIENTO' },
	{ href: '/proyecto/caracteristicas', Icon: Characteristics, label: 'FUNCIONALIDADES' },
	{ href: '/proyecto/requisitos', Icon: Requirements, label: 'CRITERIOS' },
	{ href: '/proyecto/modelo', Icon: Modeling, label: 'DIAGRAMAS' },
	{ href: '/proyecto/codigo', Icon: Implementation, label: 'CÓDIGO' },
] as const;

export function WizardNavegacion() {
	const pathname = usePathname();
	const isProyectosOpen = useProjectStore((s) => s.isProyectosOpen);

	const handleWizardClick = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			e.preventDefault();
			setPendingNavigationPath(href);
		}
	};

	if (!isProyectosOpen) return null;

	const activeIndex = phaseItems.findIndex((item) =>
		(pathname || '').startsWith(item.href),
	);

	return (
		<nav className='flex items-center justify-center gap-0 px-16 py-4 bg-linear-to-b from-neutral-50 to-neutral-0 border-b border-neutral-200'>
			{phaseItems.map(({ href, Icon, label }, index) => {
				let status: ProjectStatus = 'disable';
				if (activeIndex !== -1) {
					if (index === activeIndex) {
						status = 'active';
					} else if (index < activeIndex) {
						status = 'completed';
					}
				}

				const colors = getStyleIconStatus(status);
				const isLast = index === phaseItems.length - 1;

				return (
					<div key={href} className='flex items-center'>
						<WizardItem
							href={href}
							icon={<Icon size={18} color={colors.iconStyles} />}
							iconContainerStyles={colors.iconContainer}
							label={label}
							labelStyles={colors.labelStyles}
							onClick={handleWizardClick(href)}
						/>
						{/* Connector line between steps */}
						{!isLast && (
							<div
								className='w-20 mx-1 shrink-0 flex items-center'
								style={{ marginBottom: '20px' }}
							>
								<div
									className={`h-0.5 w-full rounded-full transition-all duration-500 ${
										index < activeIndex
											? 'bg-linear-to-r from-wizard-completed to-wizard-completed'
											: 'bg-linear-to-r from-wizard-connector-pending to-wizard-connector-pending'
									}`}
								/>
							</div>
						)}
					</div>
				);
			})}
		</nav>
	);
}
