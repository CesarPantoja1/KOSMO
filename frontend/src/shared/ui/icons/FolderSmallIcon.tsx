type Props = {
	size?: number;
	color?: string;
};

const FolderSmallIcon = ({ size = 16, color = 'text-current' }: Props) => (
	<svg
		className={`shrink-0 ${color}`}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z' />
	</svg>
);

export default FolderSmallIcon;
