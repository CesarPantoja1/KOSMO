interface CharacterCounterProps {
	current: number;
	max: number;
}
const CharacterCounter = ({ current, max }: CharacterCounterProps) => {
	const isOverLimit = current > max;
	const isNearLimit = max - current <= 7 && !isOverLimit;

	const colorClass = isOverLimit
		? 'text-error-500 font-medium'
		: isNearLimit
			? 'text-warning-500 font-medium'
			: 'text-neutral-400';

	return (
		<span
			className={`text-xs shrink-0 tabular-nums transition-colors duration-200 ${colorClass}`}
		>
			{current}/{max}
		</span>
	);
};

export { CharacterCounter };
