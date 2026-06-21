import { Search as SearchIcon } from './icons';

type Props = {
	value: string
	onChange: (value: string) => void
}

const Search = ({ value, onChange }: Props) => {
	return (
		<div className='outline outline-offset-1 outline-base-800 flex justify-start items-center rounded-sm gap-2.5 mx-0.5 pl-1'>
			<SearchIcon color='text-base-600' size={32} />
			<input
				type='text'
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className='w-xl px-2 py-1.5 focus:outline-none font-semibold'
				placeholder='Buscar Característica'
			/>
		</div>
	);
};

export default Search;
