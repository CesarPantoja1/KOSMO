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
			className='relative h-24 flex-none flex flex-col items-center justify-start text-center'
		>
			<span
				className={`flex h-18 w-18 items-center justify-center rounded-full p-5 ${iconContainerStyles}`}
			>
				{icon}
			</span>
			<span
				className={`absolute left-1/2 top-21 w-max -translate-x-1/2 whitespace-nowrap text-center text-lg leading-none ${labelStyles}`}
			>
				{label}
			</span>
		</Link>
	);
};

export default WizardItem;
