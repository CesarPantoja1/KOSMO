import { ProjectStatus } from './status';

export type ItemWizardProps = {
	href: string;
	icon: React.ReactNode;
	iconContainerStyles: string;
	label: string;
	labelStyles: string;
	onClick?: (e: React.MouseEvent) => void;
	stepNumber?: number;
	status?: ProjectStatus;
};
