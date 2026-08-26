type Props = {
	size?: number;
	color?: string;
};

const FileIcon = ({ size = 16, color = 'text-current' }: Props) => (
	<svg
		className={`shrink-0 ${color}`}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z' />
		<path d='M14 3v5h5' />
	</svg>
);

export default FileIcon;
