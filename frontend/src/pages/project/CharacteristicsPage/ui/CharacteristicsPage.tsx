import { MarkdownEditor } from '@/feature';
import { ButtonMD } from '@/shared/ui';
import { Metadata } from 'next';
import Trash from './icons/Trash';
import { Edith, Search } from './icons';
import ArrowRight from '@/shared/ui/icons/ArrowRight';

const metadata: Metadata = {
	title: 'Características - KOSMO',
	description: '',
};

const CharacteristicsPage = () => {
	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 bg-green-600'>
			<div className='flex items-center justify-between'>
				<h2 className='shrink-0 text-2xl'>Características</h2>
				<ButtonMD variant='ai'>Regenerar</ButtonMD>
				<Trash color='text-status-warning' size={24} />
				<Edith color='text-status-success' size={24} />
				<ArrowRight color='text-primary-50' size={24} />
				<Search color='text-primary-50' />
			</div>
		</div>
	);
};

export { CharacteristicsPage, metadata };
