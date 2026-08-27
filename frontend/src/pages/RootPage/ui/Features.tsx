import { Ai, Implementation, Requirements } from '@/shared/ui';

const features = [
	{
		icon: <Ai size={20} color='text-neutral-500' />,
		title: 'IA que potencia',
		text: 'La IA te acompaña desde la idea hasta el código.',
	},
	{
		icon: <Requirements size={20} color='text-neutral-500' />,
		title: 'Especificaciones claras',
		text: 'Reduce ambigüedades mediante criterios EARS.',
	},
	{
		icon: <Implementation size={20} color='text-neutral-500' />,
		title: 'Código de producción',
		text: 'Genera código estructurado para cada funcionalidad.',
	},
];

export function Features() {
	return (
		<section id='caracteristicas' className='border-t border-neutral-200 py-24'>
			<div className='mx-auto max-w-7xl px-6'>
				<div className='mx-auto max-w-2xl text-center'>
					<p className='text-xs font-medium uppercase tracking-[0.25em] text-neutral-400'>
						Diseñado para construir mejor
					</p>

					<h2 className='mt-4 text-3xl font-bold text-neutral-800 md:text-4xl'>
						Céntrate en tu negocio,
						<span className='text-neutral-800'> KOSMO se encarga del resto</span>
					</h2>
				</div>

				<div className='mt-14 grid gap-4 md:grid-cols-3'>
					{features.map((feature) => (
						<div
							key={feature.title}
							className='rounded-2xl border border-neutral-200 bg-neutral-0 p-6'
						>
							<div className='mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-100 text-xl text-neutral-500'>
								{feature.icon}
							</div>

							<h3 className='font-semibold text-neutral-800'>{feature.title}</h3>

							<p className='mt-3 text-sm leading-6 text-neutral-500'>{feature.text}</p>
						</div>
					))}
				</div>
			</div>
		</section>
	);
}
