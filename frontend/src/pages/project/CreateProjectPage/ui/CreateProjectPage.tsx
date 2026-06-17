'use client';

import { ButtonMD } from '@/shared/ui';
import { useRouter } from 'next/navigation';

const CreateProjectPage = () => {
	const router = useRouter();

	const handleSubmit = () => {
		// Aquí puedes agregar la lógica para manejar el envío del formulario
		// Por ejemplo, podrías enviar los datos a un servidor o actualizar el estado de la aplicación
		console.log('Formulario enviado');

		router.replace('/proyecto/descubrimiento');
	};

	return (
		<div>
			<h2>Crear Proyecto</h2>

			<form className='self-stretch px-8 py-3  outline-1 outline-token-color-dark-grey inline-flex flex-col justify-start items-end gap-8'>
				<div className='self-stretch flex flex-col justify-start items-start gap-3'>
					<label htmlFor='idea'>Nombre</label>
					<input
						type='text'
						id='idea'
						placeholder='Ej. Ferretería'
						className='p-3.5 py-1'
					/>
				</div>
				<div className='self-stretch flex flex-col justify-start items-start gap-3'>
					<label htmlFor='description'>Descripción</label>
					<textarea
						id='description'
						placeholder='Descripción de la idea'
						className='p-3.5 py-1'
					/>
				</div>
				<div className='size- px-8 py-2 bg-token-color-forest-green rounded-sm inline-flex justify-start items-center gap-1'>
					<ButtonMD variant='primary' onClick={handleSubmit}>
						Generar
					</ButtonMD>
				</div>
			</form>
		</div>
	);
};

export { CreateProjectPage };
