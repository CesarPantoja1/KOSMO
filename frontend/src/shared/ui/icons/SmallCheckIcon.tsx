type Props = {
	size?: number;
	color?: string;
};

const SmallCheckIcon = ({ size = 14, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='3'
	>
		<path d='M5 12l4 4L19 6' />
	</svg>
);

export default SmallCheckIcon;
