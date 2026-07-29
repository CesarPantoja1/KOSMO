import { CreateProjectForm } from './CreateProjectForm';

const CreateProjectPage = () => {
	return (
		<div className='page-container'>
			<div className='page-header mb-4'>
				<h1 className='text-base-800 text-3xl font-bold'>Crear Proyecto</h1>
				<p className='text-base-600 text-lg'>
					Define la idea central y los objetivos de tu aplicación. Una descripción clara y
					detallada le permitir; a la IA estructurar correctamente las etapas posteriores
					del desarrollo: desde la descripción general y la extracción de características,
					hasta el desglose de requisitos, el modelado y la generación de código base.
				</p>
				<CreateProjectForm />
			</div>
		</div>
	);
};

export { CreateProjectPage };
