type props = {
	size?: number;
	color: string;
};
const Plus = ({ size = 32, color }: props) => {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={size}
			height={size}
			className={`fill-current cursor-pointer ${color}`}
		>
			<path
				fillRule='evenodd'
				clipRule='evenodd'
				d='M12 3.75a.75.75 0 0 1 .75.75v6.75h6.75a.75.75 0 0 1 0 1.5h-6.75v6.75a.75.75 0 0 1-1.5 0v-6.75H4.5a.75.75 0 0 1 0-1.5h6.75V4.5a.75.75 0 0 1 .75-.75Z'
			/>
		</svg>
	);
};

export default Plus;
