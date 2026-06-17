type props = {
	size?: number;
	color: string;
};
const Right = ({ size = 32, color }: props) => {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={size}
			height={size}
			className={`fill-current ${color}`}
		>
			<path
				fill='currentColor'
				clipRule='evenodd'
				fillRule='evenodd'
				d='M16.28 11.47a.75.75 0 0 1 0 1.06l-7.5 7.5a.75.75 0 0 1-1.06-1.06L14.69 12 7.72 5.03a.75.75 0 0 1 1.06-1.06l7.5 7.5Z'
			/>
		</svg>
	);
};

export default Right;
