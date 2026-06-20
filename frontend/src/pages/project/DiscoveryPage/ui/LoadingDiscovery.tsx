import { Load } from '@/shared/ui';

const LoadingDiscovery = () => {
	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm'>
			<div className='w-full max-w-2xl rounded-xl bg-base-50 p-10 shadow-2xl outline outline-base-800'>
				<div className='flex flex-col items-center gap-8 text-center'>
					{/* Título */}
					<div className='space-y-3'>
						<h2 className='text-2xl font-semibold text-black'>
							Generando Descripción General
						</h2>

						<p className='text-base text-base-700'>
							Optimizando la estructura de la Descripción General. Por favor, espera un
							momento.
						</p>
					</div>

					<Load color='text-ai' />

					<span className='font-mono text-sm text-ai'>Cargando</span>
				</div>
			</div>
		</div>
	);
};

export default LoadingDiscovery;
