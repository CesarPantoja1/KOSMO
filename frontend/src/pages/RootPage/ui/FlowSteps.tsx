import {
	Characteristics,
	Discovery,
	Implementation,
	Modeling,
	Requirements,
} from '@/shared/ui';
import { Lightbulb } from '@/shared/ui';

const steps = [
	{
		number: '01',
		icon: <Lightbulb size={18} />,
		title: 'Idea',
		text: 'Describe tu idea de negocio.',
	},
	{
		number: '02',
		icon: <Discovery size={18} color='text-ai-500' />,
		title: 'Descubrimiento',
		text: 'La IA refina alcance, metas, actores y objetivos.',
	},
	{
		number: '03',
		icon: <Characteristics size={18} color='text-ai-500' />,
		title: 'Funcionalidades',
		text: 'Se generan las funcionalidades clave.',
	},
	{
		number: '04',
		icon: <Requirements size={18} color='text-ai-500' />,
		title: 'Criterios EARS',
		text: 'Cada funcionalidad obtiene criterios de aceptación.',
	},
	{
		number: '05',
		icon: <Modeling size={18} color='text-ai-500' />,
		title: 'Diagramas',
		text: 'Se modelan las actividades del usuario.',
	},
	{
		number: '06',
		icon: <Implementation size={18} color='text-ai-500' />,
		title: 'Código + App',
		text: 'Se genera código por funcionalidad y una app ejecutable.',
	},
];

export function FlowSteps() {
	return (
		<section
			id='como-funciona'
			className='border-t border-neutral-200 bg-neutral-50 py-24'
		>
			<div className='mx-auto max-w-7xl px-6'>
				<div className='mx-auto max-w-2xl text-center'>
					<p className='text-xs font-medium uppercase tracking-[0.25em] text-ai-500'>
						Cómo funciona
					</p>

					<h2 className='mt-4 text-3xl font-bold text-neutral-800 md:text-4xl'>
						De tu idea a una aplicación <span className='text-ai-500'>funcionando</span>
					</h2>

					<p className='mt-4 text-neutral-500'>
						KOSMO sigue un proceso estructurado para convertir conocimiento de negocio
						en software.
					</p>
				</div>

				<div className='mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-6'>
					{steps.map((step) => (
						<div
							key={step.number}
							className='group relative rounded-2xl border border-neutral-200 bg-neutral-0 p-5 transition hover:-translate-y-1 hover:border-ai-200 hover:shadow-lg hover:shadow-ai-50'
						>
							<div className='flex items-center justify-between'>
								<span className='text-xs font-medium text-ai-500'>{step.number}</span>

							<span className='flex h-10 w-10 items-center justify-center rounded-full bg-ai-50 text-lg text-ai-500'>
								{step.icon}
							</span>
							</div>

							<h3 className='mt-7 text-sm font-semibold text-neutral-800'>{step.title}</h3>

							<p className='mt-2 text-xs leading-5 text-neutral-500'>{step.text}</p>
						</div>
					))}
				</div>
			</div>
		</section>
	);
}
