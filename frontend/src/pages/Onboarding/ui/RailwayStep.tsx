'use client';

import { Railway } from '@/shared/ui';

export function RailwayStep() {
	return (
		<div className='flex flex-col gap-4'>
			<div>
				<h3 className='text-lg font-semibold text-neutral-800'>
					Conecta tu cuenta de Railway
				</h3>
				<p className='text-neutral-500 text-sm mt-1'>
					Opcional. Railway estará disponible próximamente para desplegar tus proyectos.
				</p>
			</div>
			<div className='flex items-center justify-between py-3'>
				<div className='flex items-center gap-3'>
					<div className='flex h-10 w-10 items-center justify-center rounded-lg bg-neutral-100'>
						<Railway size={20} color='text-neutral-500' />
					</div>
					<div>
						<p className='text-neutral-800 font-medium'>Railway</p>
						<p className='text-neutral-400 text-sm'>Próximamente disponible</p>
					</div>
				</div>
				<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-neutral-100 text-neutral-500'>
					Pendiente
				</span>
			</div>
		</div>
	);
}
