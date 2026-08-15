import Link from 'next/link';
import { Metadata } from 'next';
import ArrowLeft from '@/shared/ui/icons/ArrowLeft';

export const metadata: Metadata = {
	title: 'Página no encontrada',
};

export default function NotFound() {
	return (
		<section className='dark:bg-gray-900 h-full'>
			<div className='m-auto py-8 px-4 max-w-7xl lg:py-16 lg:px-6'>
				<div className='m-auto max-w-screen-sm text-center'>
					<h1 className='mb-4 text-7xl tracking-tight font-extrabold lg:text-9xl text-primary-600 dark:text-primary-500'>
						404
					</h1>
					<p className='mb-4 text-3xl tracking-tight font-bold text-gray-900 md:text-4xl dark:text-white'>
						Página no encontrada
					</p>
					<p className='mb-4 text-lg font-light text-gray-500 dark:text-gray-400'>
						La página que buscas no existe o fue movida a otra ubicación.
					</p>
					<Link href='/proyecto' className='btn btn-primary'>
						<ArrowLeft size={18} color='' />
						Back to Homepage
					</Link>
				</div>
			</div>
		</section>
	);
}
