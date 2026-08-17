import { ProjectStatus } from '../types/status';

type styles = {
	iconContainer: string;
	iconStyles: string;
	labelStyles: string;
};

export const getStyleIconStatus = (status: ProjectStatus): styles => {
	if (status === 'active')
		return {
			iconContainer:
				'border-2 border-wizard-active bg-wizard-active-light scale-110 shadow-lg animate-wizard-glow',
			iconStyles: 'text-wizard-label-active',
			labelStyles: 'text-wizard-label-active font-semibold',
		};
	if (status === 'completed')
		return {
			iconContainer: 'border-2 border-wizard-completed bg-wizard-completed shadow-md',
			iconStyles: 'text-neutral-0',
			labelStyles: 'text-wizard-label-completed font-medium',
		};

	// Default: DISABLE
	return {
		iconContainer: 'border-2 border-wizard-pending bg-wizard-pending-light',
		iconStyles: 'text-wizard-label-pending',
		labelStyles: 'text-wizard-label-pending',
	};
};
