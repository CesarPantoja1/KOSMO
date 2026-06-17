type props = {
	size?: number;
	color: string;
};

const Clock = ({ size = 32, color }: props) => {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={size}
			height={size}
			fill='none'
			strokeLinecap='round'
			strokeLinejoin='round'
			stroke='currentColor'
			strokeWidth={1.5}
			className={`stroke-current ${color}`}
		>
			<path
				strokeLinecap='round'
				strokeLinejoin='round'
				d='M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z'
			/>
		</svg>
	);
};

export default Clock;
