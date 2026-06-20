import React from 'react';
import { Edith, Trash } from './icons';

const CardCharacterist = () => {
	return (
		<div className='outline outline-base-300 inline-flex flex-col justify-center items-start gap-2.5'>
			<div className='px-8 py-4 inline-flex justify-start items-center gap-7'>
				<div className='w-14 inline-flex flex-col text-xl font-semibold justify-center items-center gap-2.5'>
					C01
				</div>
				<div className='flex-1 inline-flex flex-col justify-center gap-2.5'>
					<h3 className='text-primary-100 text-xl font-semibold'>
						Administración de Perfiles y Permisos de Usuario
					</h3>
					<p>
						Permite crear cuentas para empleados y asignarles roles específicos
						(Administrador, Cajero, Bodeguero) para restringir el acceso a pantallas y
						funciones sensibles del sistema.
					</p>
				</div>
				<div className='py-3 flex flex-col justify-end items-center gap-2'>
					<Edith color='text-status-success' size={24} />
					<Trash color='text-status-warning' size={24} />
				</div>
			</div>
		</div>
	);
};

export default CardCharacterist;
