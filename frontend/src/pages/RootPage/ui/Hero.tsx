'use client';

import { Ai, ArrowRight } from '@/shared/ui';
import {
	Characteristics,
	Discovery,
	Folder,
	Implementation,
	Modeling,
	Requirements,
} from '@/shared/ui';
import { Logo, Lightbulb, AiOrb } from '@/shared/ui';

interface HeroProps {
	onComenzar: () => void;
}

export function Hero({ onComenzar }: HeroProps) {
	return (
		<section className='relative overflow-hidden'>
			<div className='absolute inset-0 bg-linear-to-br from-ai-50 via-neutral-0 to-primary-50' />
			<div className='absolute inset-0 bg-[linear-linear(rgba(0,0,0,0.02)_1px,transparent_1px),linear-linear(90deg,rgba(0,0,0,0.02)_1px,transparent_1px)] bg-[size:60px_60px]' />

			<div className='relative mx-auto grid max-w-7xl items-center gap-14 px-6 py-24 lg:grid-cols-2 lg:py-28'>
				<div>
					<div className='mb-6 inline-flex items-center gap-2 rounded-full border border-ai-100 bg-ai-50 px-4 py-2 text-xs font-medium uppercase tracking-widest text-ai-600'>
						<Ai size={14} color='text-ai-600' />
						Spec Driven Development
					</div>

					<h1 className='max-w-2xl text-5xl font-bold leading-[1.05] tracking-tight text-neutral-800 md:text-6xl'>
						Convierte tu idea
						<br />
						en software
						<br />
						de calidad,
						<span className='block bg-linear-to-r from-ai-500 to-ai-600 bg-clip-text text-transparent'>
							guiado por IA.
						</span>
					</h1>

					<p className='mt-7 max-w-xl text-lg leading-8 text-neutral-500'>
						KOSMO toma tu idea de negocio y la transforma paso a paso en
						especificaciones claras, diagramas y código listo para construir una
						aplicación real.
					</p>

					<div className='mt-8 flex flex-wrap gap-4'>
						<button onClick={onComenzar} className='btn btn-ai btn-lg'>
							Comenzar ahora
							<ArrowRight size={16} color='text-neutral-0' />
						</button>

						<button className='btn btn-secondary btn-lg'>
							Ver cómo funciona
							<ArrowRight size={16} color='text-neutral-0' />
						</button>
					</div>

					<div className='mt-10 grid grid-cols-3 gap-5'>
						<div>
							<div className='mb-2'>
								<Lightbulb size={24} className='text-neutral-800' />
							</div>
							<p className='text-sm font-medium text-neutral-800'>Solo necesitas tu idea</p>
							<p className='mt-1 text-xs text-neutral-500'>La IA potencia lo demás</p>
						</div>

						<div>
							<div className='mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-ai-50'>
								<Ai size={16} color='text-ai-500' />
							</div>
							<p className='text-sm font-medium text-neutral-800'>IA como copiloto</p>
							<p className='mt-1 text-xs text-neutral-500'>En cada etapa del proceso</p>
						</div>

						<div>
							<div className='mb-2'>
								<AiOrb size={24} className='text-neutral-800' />
							</div>
							<p className='text-sm font-medium text-neutral-800'>Enfócate en tu negocio</p>
							<p className='mt-1 text-xs text-neutral-500'>KOSMO hace el resto</p>
						</div>
					</div>
				</div>

				{/* MOCK APP */}
				<div className='relative'>
					<div className='absolute -inset-10 rounded-full bg-ai-100/50 blur-3xl' />

					<div className='relative overflow-hidden rounded-2xl border border-neutral-200 bg-neutral-0 shadow-2xl shadow-neutral-900/10'>
						{/* APP HEADER */}
						<div className='flex items-center justify-between border-b border-neutral-200 px-5 py-4'>
							<div className='flex items-center gap-3'>
								<Logo size={28} />
								<span className='text-sm font-semibold text-neutral-800'>KOSMO</span>
							</div>

							<div className='flex gap-2'>
								<div className='h-2 w-2 rounded-full bg-neutral-200' />
								<div className='h-2 w-2 rounded-full bg-neutral-200' />
								<div className='h-2 w-2 rounded-full bg-ai-500' />
							</div>
						</div>

						<div className='grid grid-cols-[145px_1fr]'>
							{/* SIDEBAR */}
							<div className='border-r border-neutral-200 p-3'>
								<div className='mb-5 px-3 text-[10px] uppercase tracking-wider text-neutral-500'>
									Proyecto
								</div>

							{[
								{ label: 'Proyecto', icon: <Folder size={12} color='text-neutral-500' /> },
								{ label: 'Descubrimiento', icon: <Discovery size={12} color='text-ai-600' /> },
								{ label: 'Funcionalidades', icon: <Characteristics size={12} color='text-neutral-500' /> },
								{ label: 'Criterios (EARS)', icon: <Requirements size={12} color='text-neutral-500' /> },
								{ label: 'Diagramas', icon: <Modeling size={12} color='text-neutral-500' /> },
								{ label: 'Código', icon: <Implementation size={12} color='text-neutral-500' /> },
								{ label: 'Aplicación', icon: <ArrowRight size={12} color='text-neutral-500' /> },
							].map((item, index) => (
								<div
									key={item.label}
									className={`mb-1 rounded-lg px-3 py-2 text-xs ${
										index === 1 ? 'bg-ai-50 text-ai-600' : 'text-neutral-500'
									}`}
								>
									<span className='mr-2 inline-flex items-center'>
										{item.icon}
									</span>
									{item.label}
								</div>
							))}
							</div>

							{/* CONTENT */}
							<div className='p-5'>
								<div className='mb-5'>
									<p className='text-xs text-neutral-500'>Proyecto</p>
									<h3 className='mt-1 text-sm font-semibold text-neutral-800'>
										Sistema de Gestión de Reservas
									</h3>
								</div>

								<div className='mb-4 flex items-center justify-between'>
									<div>
										<h3 className='text-sm font-semibold text-neutral-800'>
											Descubrimiento
										</h3>
										<p className='mt-1 text-[11px] text-neutral-500'>
											La IA analiza y refina tu idea.
										</p>
									</div>

									<div className='flex h-9 w-9 items-center justify-center rounded-full border border-ai-100 bg-ai-50'>
										<Ai size={16} color='text-ai-500' />
									</div>
								</div>

								<div className='grid grid-cols-2 gap-3'>
									{[
										[
											'Alcance',
											'Sistema web para gestionar reservas de espacios de trabajo.',
										],
										[
											'Metas',
											'Optimizar el proceso y mejorar la experiencia del usuario.',
										],
										['Actores', 'Usuario, Administrador y Recepcionista.'],
										[
											'Objetivos',
											'Gestionar reservas y disponibilidad en tiempo real.',
										],
									].map(([title, text]) => (
										<div
											key={title}
											className='rounded-xl border border-neutral-200 bg-neutral-50 p-3'
										>
											<p className='mb-2 text-[11px] font-medium text-neutral-700'>
												{title}
											</p>
											<p className='text-[10px] leading-4 text-neutral-500'>{text}</p>
										</div>
									))}
								</div>

								<button className='btn btn-ai btn-sm mt-4'>
									Siguiente: Funcionalidades
									<ArrowRight size={14} color='text-neutral-0' />
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	);
}
