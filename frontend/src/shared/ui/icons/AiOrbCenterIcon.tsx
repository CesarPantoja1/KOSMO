type Props = {
	size?: number;
	color?: string;
};

const AiOrbCenterIcon = ({ size = 40, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='1.7'
	>
		<path d='M8 9l-4 3 4 3M16 9l4 3-4 3M14 6l-4 12' />
	</svg>
);

export default AiOrbCenterIcon;
