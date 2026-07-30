type props = {
	size?: number;
	color?: string;
};
const Check = ({ size = 24, color = 'text-current' }: props) => {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={size}
			height={size}
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
			strokeLinecap='round'
			strokeLinejoin='round'
			className={color}
		>
			<polyline points='20 6 9 17 4 12' />
		</svg>
	);
};

export default Check;
