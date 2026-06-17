type props = {
	size?: number;
	color: string;
};

const Search = ({ size = 32, color }: props) => {
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
			className={`stroke-current cursor-pointer ${color}`}
		>
			<path
				strokeLinecap='round'
				strokeLinejoin='round'
				d='m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z'
			/>
		</svg>
	);
};

export default Search;
