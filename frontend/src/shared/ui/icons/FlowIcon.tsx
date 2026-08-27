type Props = {
	size?: number;
	color?: string;
};

const FlowIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M5 4v16M5 8h8M13 8v4M13 12h6M19 12v4M13 16h6' />
	</svg>
);

export default FlowIcon;
