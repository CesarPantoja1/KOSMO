interface CharacterCounterProps {
  current: number
  max: number
}

const CharacterCounter = ({ current, max }: CharacterCounterProps) => {
  const isNearLimit = current / max >= 0.9;
  return (
    <span className={`text-xs shrink-0 tabular-nums transition-colors duration-200 ${isNearLimit ? 'text-error-500 font-medium' : 'text-neutral-400'}`}>
      {current}/{max}
    </span>
  )
}

export { CharacterCounter }

