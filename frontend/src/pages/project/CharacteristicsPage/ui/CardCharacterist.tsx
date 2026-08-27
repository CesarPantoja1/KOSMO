import { Ai, Trash } from '@/shared/ui';

type Props = {
	id: string;
	displayId: string;
	title: string;
	description: string;
	searchQuery?: string;
	isActive?: boolean;
	onRefine: (featureId: string) => void;
	onDelete: (featureId: string) => void;
};

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const highlightTitle = (title: string, query: string) => {
	if (!query) return title;
	const escaped = escapeRegex(query);
	const parts = title.split(new RegExp(`(${escaped})`, 'gi'));
	return parts.map((part, i) =>
		part.toLowerCase() === query.toLowerCase() ? (
			<span key={i} className='text-primary-600 font-semibold'>
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
	onDelete,
}: Props) => {
	return (
		<div
			className={`m-0.5 px-6 py-4 inline-flex justify-start items-center gap-6 rounded-lg transition-all bg-neutral-0 ${
				isActive
					? 'border-2 border-primary-500 shadow-md'
					: 'border border-neutral-200 hover:border-neutral-300 hover:shadow-sm'
			}`}
		>
			{/* ID */}
			<div
				className={`w-12 inline-flex flex-col text-base font-bold justify-center items-center shrink-0 ${
					isActive ? 'text-primary-500' : 'text-neutral-400'
				}`}
			>
				{displayId}
			</div>

			{/* Content */}
			<div className='flex-1 inline-flex flex-col justify-center gap-1.5'>
				<h3
					className={`text-base font-semibold ${isActive ? 'text-primary-600' : 'text-neutral-800'}`}
				>
					{highlightTitle(title, searchQuery)}
				</h3>
				<p className='text-neutral-500 text-sm'>{description}</p>
			</div>

			{/* Actions */}
			<div className='flex items-center gap-1 shrink-0'>
				<button
					onClick={() => onRefine(id)}
					disabled={isActive}
					title={isActive ? 'Refinando con IA' : 'Mejorar con IA'}
					className={`p-2 rounded-lg border border-transparent cursor-pointer disabled:cursor-default transition-colors inline-flex items-center justify-center ${
						isActive
							? 'bg-ai-50 text-ai-500 border-ai-100'
							: 'text-neutral-400 hover:text-ai-500 hover:bg-ai-50 hover:border-ai-100'
					}`}
				>
					<Ai size={16} color={isActive ? 'text-ai-500' : 'text-current'} />
				</button>
				<button
					onClick={() => onDelete(id)}
					title='Eliminar'
					className='p-2 rounded-lg border border-transparent cursor-pointer transition-colors inline-flex items-center justify-center text-neutral-400 hover:text-error-500 hover:bg-error-50 hover:border-error-100'
				>
					<Trash size={16} />
				</button>
			</div>
		</div>
	);
};

export default CardCharacterist;
