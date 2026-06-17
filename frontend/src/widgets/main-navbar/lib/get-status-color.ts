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
				'border-2 border-status-warning bg-light-yellow shadow-md shadow-status-warning ',
			iconStyles: 'text-status-warning',
			labelStyles: 'text-status-warning',
		};
	if (status === 'completed')
		return {
			iconContainer: 'border-[1px] border-primary-100 bg-primary-100',
			iconStyles: 'text-base-50',
			labelStyles: 'text-primary-100',
		};

	// Default: DISABLE
	return {
		iconContainer: 'border-[1px] border-base-600 bg-base-50 ',
		iconStyles: 'text-base-600',
		labelStyles: 'text-base-600',
	};
};
