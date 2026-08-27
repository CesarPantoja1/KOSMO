type Props = {
	size?: number;
	color?: string;
};

const ScreensIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<rect x='3' y='4' width='18' height='16' rx='2' />
		<path d='M3 9h18M8 14h3M8 17h6' />
	</svg>
);

export default ScreensIcon;
