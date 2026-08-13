import Link from 'next/link';
import { ItemWizardProps } from '../types/wizard';

const WizardItem = ({
	href,
	icon,
	iconContainerStyles,
	label,
	labelStyles,
	onClick,
	stepNumber,
	status,
}: ItemWizardProps) => {
	return (
		<Link
			href={href}
			onClick={onClick}
			className='group relative flex-none flex flex-col items-center justify-start text-center gap-2 px-3 py-1 transition-all duration-200 hover:scale-105'
		>
		<span
			className={`flex h-11 w-11 items-center justify-center rounded-full transition-all duration-300 ${iconContainerStyles}`}
		>
			{icon}
		</span>
			<span
				className={`whitespace-nowrap text-center text-xs leading-none transition-colors duration-200 ${labelStyles}`}
			>
				{label}
			</span>
		</Link>
	);
};

export default WizardItem;
