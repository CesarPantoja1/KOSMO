const LoadingDiscovery = () => {
	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm'>
			<div className='w-full max-w-2xl rounded-xl bg-base-50 p-10 shadow-2xl outline outline-1 outline-base-800'>
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

					{/* Estado */}
					<div className='flex items-center gap-3'>
						{/* Spinner */}
						<div className='flex h-16 w-16 items-center justify-center rounded-full border border-base-300'>
							<div className='h-8 w-8 animate-spin rounded-full border-[3px] border-base-300 border-t-ai' />
						</div>
					</div>
					<span className='font-mono text-sm text-ai'>Cargando...</span>
				</div>
			</div>
		</div>
	);
};

export default LoadingDiscovery;
