import { Search as SearchIcon } from '@/shared/ui';

type Props = {
	value: string;
	onChange: (value: string) => void;
};

const Search = ({ value, onChange }: Props) => {
	return (
		<div className='flex items-center gap-2 rounded-md border border-neutral-300 bg-neutral-50 px-3 py-2 transition-colors focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20'>
			<SearchIcon color='text-neutral-400' size={16} />
			<input
				type='text'
				value={value}
				onChange={(e) => {
					const val = e.target.value.replace(/[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]/g, '');
					onChange(val);
				}}
				className='w-full bg-transparent text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none font-normal'
				placeholder='Buscar funcionalidad...'
			/>
		</div>
	);
};

export default Search;
