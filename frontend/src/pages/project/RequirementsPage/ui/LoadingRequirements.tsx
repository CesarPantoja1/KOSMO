import { Load } from '@/shared/ui';

const LoadingRequirements = () => {
	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/60'>
			<div className='w-1/2 p-7 bg-base-50 outline outline-base-300 inline-flex flex-col justify-center items-center gap-7 rounded-md'>
				<div className='flex flex-col justify-center items-center gap-4'>
					<h2 className='justify-start text-black text-2xl font-semibold'>
						Generando requisitos...
					</h2>
					<p className='flex-1 text-center justify-start text-black text-base font-normal'>
						Desglosando la característica seleccionada en especificaciones técnicas.
					</p>
				</div>
				<Load color='text-ai' />
				<span className='text-ai text-sm font-normal font-mono'>Cargando</span>
			</div>
		</div>
	);
};

export default LoadingRequirements;
