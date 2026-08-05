'use client';

import Link from 'next/link';

const ImplementationPage = () => {
	return (
		<div className='flex min-h-full items-center justify-center px-6'>
			<div className='w-full max-w-2xl'>
				<div className='mx-auto flex h-20 w-20 items-center justify-center rounded-full border border-base-300 bg-base-100 text-4xl'>
					🚧
				</div>

				<h1 className='mt-6 text-3xl font-bold text-base-800'>Módulo en desarrollo</h1>

				<p className='mt-4 text-base leading-7 text-base-600'>
					La etapa de <span className='font-semibold text-base-800'>Implementación</span>{' '}
					se encuentra actualmente en construcción.
				</p>

				<p className='mt-2 text-base leading-7 text-base-600'>
					Próximamente podrás generar, visualizar y administrar el código fuente a partir
					de los modelos definidos en tu proyecto.
				</p>

				<div className='mt-8 rounded-xl border border-status-warning/20 bg-status-warning/10 px-4 py-3 text-sm text-status-warning'>
					Esta funcionalidad estará disponible en una próxima actualización.
				</div>

				<div className='mt-8 border-t border-base-300 pt-6 text-sm text-base-600'>
					<span>Mientras tanto, puedes continuar trabajando en las etapas de </span>
					<Link href='/proyecto/descubrimiento' className='font-medium text-primary-100 hover:underline'>
						Descubrimiento
					</Link>
					<span>, </span>
					<Link href='/proyecto/caracteristicas' className='font-medium text-primary-100 hover:underline'>
						Características
					</Link>
					<span>, </span>
					<Link href='/proyecto/requisitos' className='font-medium text-primary-100 hover:underline'>
						Requisitos
					</Link>
					<span> y </span>
					<Link href='/proyecto/modelo' className='font-medium text-primary-100 hover:underline'>
						Modelado
					</Link>
					<span>.</span>
				</div>
			</div>
		</div>
	);
};

export { ImplementationPage };
