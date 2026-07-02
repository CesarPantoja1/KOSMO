type props = {
	size?: number;
	color: string;
};

const Send = ({ size = 32, color }: props) => {
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
				d='M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5'
			/>
		</svg>
	);
};

export default Send;
