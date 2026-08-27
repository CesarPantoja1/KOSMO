type Props = {
	size?: number;
	color?: string;
};

const SuccessCheckIcon = ({ size = 40, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M5 12l4 4L19 6' />
	</svg>
);

export default SuccessCheckIcon;
