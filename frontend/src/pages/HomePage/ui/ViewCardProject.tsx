import { Project } from '@/entities/project';
import { Plus } from '@/shared/ui';
import { Link } from 'react-aria-components';
import { Clock } from './icons';

type props = {
	projects: Project[];
	handleProjectClick: (a: Project) => void;
};

const ViewCardProject = ({ projects, handleProjectClick }: props) => {
	return (
		<div className='grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5 max-w-450'>
			{/* Create new card */}
			<Link
				href='/crear-proyecto'
				className='flex min-h-40 flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-neutral-300 bg-neutral-50 p-5 transition-all hover:border-primary-500 hover:bg-primary-50 hover:shadow-md group hover:scale-95'
			>
				<div className='flex h-10 w-10 items-center justify-center rounded-full bg-neutral-200 group-hover:bg-primary-100 transition-colors'>
					<Plus color='text-neutral-500 group-hover:text-primary-600' />
				</div>
				<div className='text-center'>
					<p className='text-neutral-700 font-semibold group-hover:text-primary-600 transition-colors'>
						Crear nuevo proyecto
					</p>
					<p className='text-neutral-400 text-sm mt-0.5'>Comienza una nueva iniciativa</p>
				</div>
			</Link>

			{/* Project cards */}
			{projects.map((project) => (
				<article
					key={project.id}
					onClick={() => handleProjectClick(project)}
					className='flex min-h-40 cursor-pointer flex-col rounded-lg bg-neutral-0 p-5 shadow-sm border border-neutral-200 transition-all hover:shadow-md hover:scale-95 hover:border-neutral-300'
				>
					<header>
						<h3 className='truncate text-lg font-semibold text-neutral-800 capitalize'>
							{project.name}
						</h3>
					</header>

					<p className='mt-2 line-clamp-2 text-sm text-neutral-500 capitalize flex-1'>
						{project.description || 'Sin descripción'}
					</p>

					<div className='flex items-center gap-3 pt-3 mt-3 border-t border-neutral-100'>
						<div className='flex items-center gap-1.5'>
							<Clock size={13} color='text-neutral-400' />
							<span className='text-xs text-neutral-400'>
								{new Date(project.created_at).toLocaleDateString()}
							</span>
						</div>
						{project.current_phase && (
							<span className='text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full'>
								{project.current_phase}
							</span>
						)}
						<div className='ml-auto flex items-center gap-1.5'>
							<div className='w-1.5 h-1.5 rounded-full bg-primary-500' />
							<span className='text-xs text-primary-500 font-medium'>
								{project.status || 'En progreso'}
							</span>
						</div>
					</div>
				</article>
			))}
		</div>
	);
};

export default ViewCardProject;
