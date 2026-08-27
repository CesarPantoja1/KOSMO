import { Project } from '@/entities/project';
import { Plus, Trash, ModalConfirm } from '@/shared/ui';
import { Link } from 'react-aria-components';
import { useState } from 'react';
import { Clock, toast } from '@/shared/ui';
import { formatApiError } from '@/shared/api';
import { useProjectStore } from '@/entities/project';

type props = {
	projects: Project[];
	handleProjectClick: (a: Project) => void;
};

const ViewTableProject = ({ projects, handleProjectClick }: props) => {
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
	const deleteProjectStore = useProjectStore((s) => s.deleteProject);

	const handleDelete = async () => {
		if (!confirmDeleteId) return;
		const id = confirmDeleteId;
		setConfirmDeleteId(null);
		try {
			await deleteProjectStore(id);
			toast.success('Proyecto eliminado');
		} catch (err) {
			toast.error(formatApiError(err, 'Error al eliminar el proyecto'));
		}
	};

	return (
		<>
			<table className='w-full flex-1'>
				<thead className='sticky top-0 z-10'>
					<tr className='bg-neutral-100 border-b border-neutral-200'>
						<th className='px-4 py-3 text-left text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
							Proyecto
						</th>
						<th className='w-44 px-4 py-3 text-left text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
							Fase Actual
						</th>
						<th className='w-44 px-4 py-3 text-center text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
							Estado
						</th>
						<th className='w-44 px-4 py-3 text-right text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
							Creado
						</th>
						<th className='w-20 px-4 py-3 text-center text-neutral-600 text-sm font-semibold uppercase tracking-wide'>
							Acciones
						</th>
					</tr>
				</thead>

				<tbody>
					{projects.length === 0 && (
						<tr>
							<td
								colSpan={5}
								className='p-8 bg-neutral-0 text-center text-neutral-400 text-sm'
							>
								No tienes proyectos creados. Crea tu primer proyecto para comenzar.
							</td>
						</tr>
					)}

					{projects.map((project, index) => (
						<tr
							key={project.id}
							onClick={() => handleProjectClick(project)}
							className={`cursor-pointer border-b border-neutral-100 transition-colors hover:bg-primary-50 ${
								index % 2 === 0 ? 'bg-neutral-0' : 'bg-neutral-50'
							}`}
						>
							<td className='p-4'>
								<div className='flex flex-col gap-1'>
									<h3 className='text-neutral-800 text-sm font-semibold truncate capitalize'>
										{project.name}
									</h3>
									<p className='text-neutral-400 text-xs'>
										{project.description || 'Sin descripción'}
									</p>
								</div>
							</td>

							<td className='w-44 p-4 text-neutral-600 text-sm capitalize'>
								{project.current_phase || 'Descubrimiento'}
							</td>

							<td className='w-44 p-4'>
								<div className='flex justify-center'>
									<div className='px-3 py-1 bg-primary-50 border border-primary-100 rounded-full flex items-center gap-2'>
										<Clock size={13} color='text-primary-500' />
										<span className='text-primary-500 text-xs font-medium'>
											{project.status || 'En progreso'}
										</span>
									</div>
								</div>
							</td>

							<td className='w-44 p-4 text-right text-neutral-400 text-xs'>
								<time dateTime={project.created_at}>
									{new Date(project.created_at).toLocaleDateString()}
								</time>
							</td>

							<td className='w-20 p-4'>
								<div className='flex justify-center'>
									<button
										onClick={(e) => {
											e.stopPropagation();
											setConfirmDeleteId(project.id);
										}}
										className='p-1.5 rounded-md hover:bg-error-50 transition-colors cursor-pointer'
										title='Eliminar proyecto'
									>
										<Trash size={16} color='text-error-500' />
									</button>
								</div>
							</td>
						</tr>
					))}
				</tbody>

				<tfoot className='sticky bottom-0 bg-neutral-100 border-t border-neutral-200'>
					<tr>
						<td colSpan={5} className='px-4 text-left'>
							<Link
								href='/crear-proyecto'
								className='py-3 inline-flex items-center gap-2 text-neutral-500 hover:text-primary-500 transition-colors'
							>
								<div className='flex h-7 w-7 items-center justify-center rounded-md border border-neutral-300 hover:border-primary-500 transition-colors'>
									<Plus color='text-current' />
								</div>
								<span className='text-sm font-medium'>Crear nuevo proyecto</span>
							</Link>
						</td>
					</tr>
				</tfoot>
			</table>

			{confirmDeleteId && (
				<ModalConfirm
					title='Eliminar proyecto'
					description='Esta acción no se puede deshacer. ¿Estás seguro de eliminar este proyecto?'
					cancelText='Cancelar'
					confirmText='Eliminar'
					onCancel={() => setConfirmDeleteId(null)}
					onConfirm={handleDelete}
				/>
			)}
		</>
	);
};
export default ViewTableProject;
