import { CreateProjectForm } from './CreateProjectForm';

const CreateProjectPage = () => {
	return (
		<div className='p-8 flex flex-col gap-2.5 h-full'>
			<div className='flex flex-col justify-start items-start gap-2.5'>
				<h1 className='text-base-800 text-3xl font-bold'>Crear Proyecto</h1>
				<p className='text-base-800 text-lg'>
					Define la idea central y los objetivos de tu aplicaci&oacute;n. Una
					descripci&oacute;n clara y detallada le permitir&aacute; a la IA estructurar
					correctamente las etapas posteriores del desarrollo: desde la descripci&oacute;n
					general y la extracci&oacute;n de caracter&iacute;sticas, hasta el desglose de
					requisitos, el modelado y la generaci&oacute;n de c&oacute;digo base.
				</p>
			</div>
			<CreateProjectForm />
		</div>
	);
};

export { CreateProjectPage };
