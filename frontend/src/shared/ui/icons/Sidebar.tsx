type props = {
	size?: number;
	color: string;
};

const Sidebar = ({ size = 32, color }: props) => {
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
			className={`stroke-current cursor-pointer ${color}`}
		>
			<path
				fill='none'
				d='M4 6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2H6a2 2 0 0 1 -2 -2z'
			/>
			<path fill='none' d='m9 4 0 16' />
		</svg>
	);
};

export default Sidebar;
