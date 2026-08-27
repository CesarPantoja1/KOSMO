type Props = {
	size?: number;
	color?: string;
};

const EntitiesIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<ellipse cx='12' cy='5' rx='7' ry='3' />
		<path d='M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5' />
		<path d='M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7' />
	</svg>
);

export default EntitiesIcon;
