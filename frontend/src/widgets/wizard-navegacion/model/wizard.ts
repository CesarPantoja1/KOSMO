export type ItemWizardProps = {
	href: string;
	icon: React.ReactNode;
	iconContainerStyles: string;
	label: string;
	subtitle: string;
	labelStyles: string;
	onClick?: (e: React.MouseEvent) => void;
};
