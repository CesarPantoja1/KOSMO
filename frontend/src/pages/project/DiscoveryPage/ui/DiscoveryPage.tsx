import { MarkdownEditor } from '@/feature';
import { ButtonMD } from '@/shared/ui';
import { Metadata } from 'next';

const metadata: Metadata = {
	title: 'Descubrimiento - KOSMO',
	description: '',
};

const DiscoveryPage = () => {
	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 bg-green-600'>
			<div className='flex items-center justify-between'>
				<h2 className='shrink-0 text-2xl'>Descripción General del Producto</h2>
				<ButtonMD variant='ai'>Regenerar</ButtonMD>
			</div>
			<MarkdownEditor />
		</div>
	);
};

export { DiscoveryPage, metadata };
