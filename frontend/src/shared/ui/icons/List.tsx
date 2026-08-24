type props = {
	size?: number;
	color: string;
};

const List = ({ size = 32, color }: props) => {
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
				d='M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z'
			/>
		</svg>
	);
};

export default List;
