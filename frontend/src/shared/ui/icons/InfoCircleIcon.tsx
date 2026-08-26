type Props = {
	size?: number;
	color?: string;
};

const InfoCircleIcon = ({ size = 16, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<circle cx='12' cy='12' r='9' />
		<path d='M12 11v5M12 8h.01' />
	</svg>
);

export default InfoCircleIcon;
