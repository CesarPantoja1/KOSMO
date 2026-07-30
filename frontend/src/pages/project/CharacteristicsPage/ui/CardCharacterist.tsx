import { Ai } from '@/shared/ui';
import { Trash } from './icons';

type Props = {
	id: string;
	displayId: string;
	title: string;
	description: string;
	searchQuery?: string;
	isActive?: boolean;
	onRefine: (featureId: string) => void;
};

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const highlightTitle = (title: string, query: string) => {
	if (!query) return title;
	const escaped = escapeRegex(query);
	const parts = title.split(new RegExp(`(${escaped})`, 'gi'));
	return parts.map((part, i) =>
		part.toLowerCase() === query.toLowerCase() ? (
			<span key={i} className='text-primary-800'>
				{part}
			</span>
		) : (
			part
		),
	);
};

const CardCharacterist = ({
	id,
	displayId,
	title,
	description,
	searchQuery = '',
	isActive = false,
	onRefine,
}: Props) => {
	return (
		<div
			className={`m-0.5 px-8 py-4 inline-flex justify-start items-center gap-7 transition-shadow ${
				isActive
					? 'outline outline-primary-100 shadow-md'
					: 'outline outline-base-300 hover:shadow-md'
			}`}
		>
			<div className='w-14 inline-flex flex-col text-xl font-semibold justify-center items-center gap-2.5'>
				{displayId}
			</div>
			<div className='flex-1 inline-flex flex-col justify-center gap-2.5'>
				<h3 className='text-primary-100 text-xl font-semibold'>
					{highlightTitle(title, searchQuery)}
				</h3>
				<p className='line-clamp-2 text-base-800 text-ellipsis overflow-hidden'>
					{description}
				</p>
			</div>
			<div className='py-3 flex flex-col justify-end items-center gap-2'>
				<button
					onClick={() => onRefine(id)}
					disabled={isActive}
					title={isActive ? 'Refinando' : 'Refinar'}
					className={`p-2 rounded-full border border-transparent cursor-pointer disabled:cursor-default transition-colors inline-flex items-center justify-center ${
						isActive
							? 'bg-base-100 shadow-sm text-ai'
							: 'text-base-600 hover:text-base-800 hover:bg-base-100 active:text-ai'
					}`}
				>
					<Ai size={16} color={isActive ? 'text-ai' : 'text-current'} />
				</button>
				<button className='cursor-pointer'>
					<Trash color='text-base-600 hover:text-status-error' size={24} />
				</button>
			</div>
		</div>
	);
};

export default CardCharacterist;
