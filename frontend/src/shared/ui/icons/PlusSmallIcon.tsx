type Props = {
	size?: number;
	color?: string;
};

const PlusSmallIcon = ({ size = 16, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M12 3v18M3 12h18' />
	</svg>
);

export default PlusSmallIcon;
