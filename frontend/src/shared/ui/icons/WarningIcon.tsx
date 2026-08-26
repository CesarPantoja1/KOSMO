type Props = {
	size?: number;
	color?: string;
};

const WarningIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={`shrink-0 ${color}`}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<circle cx='12' cy='12' r='9' />
		<path d='M12 8v4M12 16h.01' />
	</svg>
);

export default WarningIcon;
