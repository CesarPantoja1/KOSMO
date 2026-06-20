import { Search as SearchIcon } from './icons';

const Search = () => {
	return (
		<div className='outline outline-offset-1 outline-base-800 flex justify-start items-center rounded-sm gap-2.5 mx-0.5 pl-1'>
			<SearchIcon color='text-base-600' size={32} />
			<input
				type='text'
				className='w-xl px-2 py-1.5 focus:outline-none font-semibold'
				placeholder='Buscar Característica'
			/>
		</div>
	);
};

export default Search;
