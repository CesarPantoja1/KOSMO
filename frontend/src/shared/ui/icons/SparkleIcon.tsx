type Props = {
	size?: number;
	color?: string;
};

const SparkleIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='currentColor'
	>
		<path d='M12 1l1.5 6.5L20 9l-6.5 1.5L12 17l-1.5-6.5L4 9l6.5-1.5L12 1z' />
	</svg>
);

export default SparkleIcon;
