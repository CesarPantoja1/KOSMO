type props = {
	size?: number;
	color?: string;
};

const Check = ({ size = 24, color = '' }: props) => {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={size}
			height={size}
			className={color}
		>
			<polyline
				points='20 6 9 17 4 12'
				style={{ stroke: 'currentColor', fill: 'none' }}
				strokeWidth='2'
				strokeLinecap='round'
				strokeLinejoin='round'
			/>
		</svg>
	);
};

export default Check;
