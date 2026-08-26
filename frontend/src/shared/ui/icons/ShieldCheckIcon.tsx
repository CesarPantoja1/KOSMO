type Props = {
	size?: number;
	color?: string;
};

const ShieldCheckIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M12 3l8 4v5c0 4.5-3.4 7.8-8 9-4.6-1.2-8-4.5-8-9V7l8-4z' />
		<path d='M9 12l2 2 4-4' />
	</svg>
);

export default ShieldCheckIcon;
