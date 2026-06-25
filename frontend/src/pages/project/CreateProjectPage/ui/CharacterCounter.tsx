interface CharacterCounterProps {
  current: number
  max: number
}

const CharacterCounter = ({ current, max }: CharacterCounterProps) => {
  return (
    <span className='text-sm text-base-600 shrink-0'>
      {current}/{max}
    </span>
  )
}

export { CharacterCounter }
