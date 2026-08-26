type Props = {
	size?: number;
	color?: string;
};

const RulesIcon = ({ size = 20, color = 'text-current' }: Props) => (
	<svg
		className={color}
		viewBox='0 0 24 24'
		width={size}
		height={size}
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M13 2L3 14h9l-1 8 10-12h-9l1-8z' />
	</svg>
);

export default RulesIcon;
