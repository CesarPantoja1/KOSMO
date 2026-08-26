type Props = {
	size?: number;
	color?: string;
};

const StarIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M12 2l3 6 6 .9-4.5 4.4 1 6.2-5.5-3-5.5 3 1-6.2L3 8.9 9 8l3-6z' />
	</svg>
);

export default StarIcon;
