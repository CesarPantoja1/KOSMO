import Link from 'next/link';
import { ItemWizardProps } from '../types/wizard';

const WizardItem = ({
	href,
	icon,
	iconContainerStyles,
	label,
	labelStyles,
	onClick,
}: ItemWizardProps) => {
	return (
		<Link
			href={href}
			onClick={onClick}
			className='relative h-20 flex-none flex flex-col items-center justify-start text-center'
		>
			<span
				className={`flex h-14 w-14 items-center justify-center rounded-full ${iconContainerStyles}`}
			>
				{icon}
			</span>
			<span
				className={`absolute left-1/2 top-16 w-max -translate-x-1/2 whitespace-nowrap text-center text-sm font-medium leading-none ${labelStyles}`}
			>
				{label}
			</span>
		</Link>
	);
};

export default WizardItem;
