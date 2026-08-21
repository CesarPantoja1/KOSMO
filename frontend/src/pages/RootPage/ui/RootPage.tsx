'use client';

import { Ai, ArrowRight } from '@/shared/ui';
import { useState } from 'react';
import { Login } from './Login';
import { Register } from './Register';

export function RootPage() {
	const [showAuthModal, setShowAuthModal] = useState(false);
	const [authView, setAuthView] = useState<'login' | 'register'>('login');

	const openLoginModal = () => {
		setAuthView('login');
		setShowAuthModal(true);
	};

	return (
		<div className='min-h-screen bg-neutral-0 text-neutral-800'>
			{/* NAVBAR */}
			<header className='sticky top-0 z-50 border-b border-neutral-200 bg-neutral-0/90 backdrop-blur-xl'>
				<div className='mx-auto flex h-20 max-w-7xl items-center justify-between px-6'>
					<div className='flex items-center gap-3'>
						<div className='flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-ai-500 to-ai-600 text-xl font-bold text-neutral-0'>
							K
						</div>

						<span className='text-xl font-bold tracking-tight text-neutral-800'>KOSMO</span>
					</div>

					<nav className='hidden items-center gap-8 text-sm text-neutral-500 md:flex'>
						<a href='#caracteristicas' className='transition hover:text-neutral-800'>
							Características
						</a>
						<a href='#como-funciona' className='transition hover:text-neutral-800'>
							Cómo funciona
						</a>
						<a href='#metodologia' className='transition hover:text-neutral-800'>
							Metodología
						</a>
						<a href='#precios' className='transition hover:text-neutral-800'>
							Precios
						</a>
						<a href='#docs' className='transition hover:text-neutral-800'>
							Docs
						</a>
					</nav>

					<button onClick={openLoginModal} className='btn btn-ai btn-sm'>
						Comenzar
					</button>
				</div>
			</header>

			{/* HERO */}
			<section className='relative overflow-hidden'>
				<div className='absolute inset-0 bg-gradient-to-br from-ai-50 via-neutral-0 to-primary-50' />
				<div className='absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.02)_1px,transparent_1px)] bg-[size:60px_60px]' />

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
							<span className='block bg-gradient-to-r from-ai-500 to-ai-600 bg-clip-text text-transparent'>
								guiado por IA.
							</span>
						</h1>

						<p className='mt-7 max-w-xl text-lg leading-8 text-neutral-500'>
							KOSMO toma tu idea de negocio y la transforma paso a paso en
							especificaciones claras, diagramas y código listo para construir una
							aplicación real.
						</p>

						<div className='mt-8 flex flex-wrap gap-4'>
							<button onClick={openLoginModal} className='btn btn-ai btn-lg'>
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
								<div className='mb-2 text-2xl'>💡</div>
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
								<div className='mb-2 text-2xl'>◎</div>
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
									<div className='flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-ai-500 to-ai-600 text-xs font-bold text-neutral-0'>
										K
									</div>
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
										'Proyecto',
										'Descubrimiento',
										'Funcionalidades',
										'Criterios (EARS)',
										'Diagramas',
										'Código',
										'Aplicación',
									].map((item, index) => (
										<div
											key={item}
											className={`mb-1 rounded-lg px-3 py-2 text-xs ${
												index === 1 ? 'bg-ai-50 text-ai-600' : 'text-neutral-500'
											}`}
										>
											<span className='mr-2'>
												{['⌂', '◈', '▦', '◇', '⌘', '</>', '↗'][index]}
											</span>
											{item}
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
											<h3 className='text-sm font-semibold text-neutral-800'>Descubrimiento</h3>
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

			{/* FLOW */}
			<section id='como-funciona' className='border-t border-neutral-200 bg-neutral-50 py-24'>
				<div className='mx-auto max-w-7xl px-6'>
					<div className='mx-auto max-w-2xl text-center'>
						<p className='text-xs font-medium uppercase tracking-[0.25em] text-ai-500'>
							Cómo funciona
						</p>

						<h2 className='mt-4 text-3xl font-bold text-neutral-800 md:text-4xl'>
							De tu idea a una aplicación{' '}
							<span className='text-ai-500'>funcionando</span>
						</h2>

						<p className='mt-4 text-neutral-500'>
							KOSMO sigue un proceso estructurado para convertir conocimiento de negocio
							en software.
						</p>
					</div>

					<div className='mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-6'>
						{[
							{
								number: '01',
								icon: '💡',
								title: 'Idea',
								text: 'Describe tu idea de negocio.',
							},
							{
								number: '02',
								iconComponent: <Ai size={18} />,
								title: 'Descubrimiento',
								text: 'La IA refina alcance, metas, actores y objetivos.',
							},
							{
								number: '03',
								icon: '▦',
								title: 'Funcionalidades',
								text: 'Se generan las funcionalidades clave.',
							},
							{
								number: '04',
								icon: '◇',
								title: 'Criterios EARS',
								text: 'Cada funcionalidad obtiene criterios de aceptación.',
							},
							{
								number: '05',
								icon: '⌘',
								title: 'Diagramas',
								text: 'Se modelan las actividades del usuario.',
							},
							{
								number: '06',
								icon: '</>',
								title: 'Código + App',
								text: 'Se genera código por funcionalidad y una app ejecutable.',
							},
						].map((step) => (
							<div
								key={step.number}
								className='group relative rounded-2xl border border-neutral-200 bg-neutral-0 p-5 transition hover:-translate-y-1 hover:border-ai-200 hover:shadow-lg hover:shadow-ai-50'
							>
								<div className='flex items-center justify-between'>
									<span className='text-xs font-medium text-ai-500'>
										{step.number}
									</span>

									<span className='flex h-10 w-10 items-center justify-center rounded-full bg-ai-50 text-lg text-ai-500'>
										{'iconComponent' in step ? step.iconComponent : step.icon}
									</span>
								</div>

								<h3 className='mt-7 text-sm font-semibold text-neutral-800'>{step.title}</h3>

								<p className='mt-2 text-xs leading-5 text-neutral-500'>{step.text}</p>
							</div>
						))}
					</div>
				</div>
			</section>

			{/* FEATURES */}
			<section id='caracteristicas' className='border-t border-neutral-200 py-24'>
				<div className='mx-auto max-w-7xl px-6'>
					<div className='mx-auto max-w-2xl text-center'>
						<p className='text-xs font-medium uppercase tracking-[0.25em] text-ai-500'>
							Diseñado para construir mejor
						</p>

						<h2 className='mt-4 text-3xl font-bold text-neutral-800 md:text-4xl'>
							Céntrate en tu negocio,
							<span className='text-ai-500'> KOSMO se encarga del resto</span>
						</h2>
					</div>

					<div className='mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-5'>
						{[
							{
								icon: <Ai size={20} color='text-ai-500' />,
								title: 'IA que potencia',
								text: 'La IA te acompaña desde la idea hasta el código.',
							},
							{
								icon: '◈',
								title: 'Especificaciones claras',
								text: 'Reduce ambigüedades mediante criterios EARS.',
							},
							{
								icon: '⌘',
								title: 'Modelado',
								text: 'Visualiza las actividades del usuario con diagramas.',
							},
							{
								icon: '</>',
								title: 'Código de producción',
								text: 'Genera código estructurado para cada funcionalidad.',
							},
							{
								icon: <ArrowRight size={20} color='text-ai-500' />,
								title: 'Aplicación funcional',
								text: 'Visualiza directamente la aplicación construida.',
							},
						].map((feature) => (
							<div
								key={feature.title}
								className='rounded-2xl border border-neutral-200 bg-neutral-0 p-6'
							>
								<div className='mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-ai-50 text-xl text-ai-500'>
									{feature.icon}
								</div>

								<h3 className='font-semibold text-neutral-800'>{feature.title}</h3>

								<p className='mt-3 text-sm leading-6 text-neutral-500'>{feature.text}</p>
							</div>
						))}
					</div>
				</div>
			</section>

			{/* SDD */}
			<section id='metodologia' className='border-t border-neutral-200 py-24'>
				<div className='mx-auto grid max-w-7xl items-center gap-14 px-6 lg:grid-cols-2'>
					<div>
						<p className='text-xs font-medium uppercase tracking-[0.25em] text-ai-500'>
							La metodología
						</p>

						<h2 className='mt-4 text-4xl font-bold text-neutral-800'>
							Spec Driven
							<span className='text-ai-500'> Development</span>
						</h2>

						<p className='mt-6 leading-8 text-neutral-500'>
							KOSMO utiliza Spec Driven Development para que el software no empiece
							directamente con código. Primero se entiende el problema, se define el
							comportamiento esperado y después se construye.
						</p>

						<div className='mt-8 space-y-4'>
							{[
								'Primero entendemos el negocio.',
								'Después definimos qué debe hacer el sistema.',
								'Convertimos las funcionalidades en especificaciones.',
								'Modelamos el comportamiento esperado.',
								'Finalmente generamos el código.',
							].map((item, index) => (
								<div key={item} className='flex items-center gap-4'>
									<div className='flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-50 text-xs text-ai-600'>
										{index + 1}
									</div>

									<span className='text-sm text-neutral-700'>{item}</span>
								</div>
							))}
						</div>
					</div>

					<div className='rounded-3xl border border-neutral-200 bg-neutral-50 p-8'>
						<div className='mb-8 flex items-center justify-between'>
							<div>
								<p className='text-xs text-neutral-500'>KOSMO Method</p>
								<h3 className='mt-1 text-lg font-semibold text-neutral-800'>
									Idea → Specification → Software
								</h3>
							</div>

							<div className='flex h-12 w-12 items-center justify-center rounded-xl bg-ai-50 text-xl text-ai-500'>
								<Ai size={20} color='text-ai-500' />
							</div>
						</div>

						<div className='space-y-3'>
							{[
								['01', 'Business Idea', 'Tu conocimiento'],
								['02', 'Discovery', 'IA'],
								['03', 'Functionalities', 'IA + negocio'],
								['04', 'EARS Criteria', 'Especificación'],
								['05', 'Activity Diagrams', 'Modelo'],
								['06', 'Code', 'Generación'],
							].map(([number, title, description], index) => (
								<div key={number}>
									<div className='flex items-center gap-4 rounded-xl border border-neutral-200 bg-neutral-0 p-4'>
										<span className='text-xs font-medium text-ai-500'>{number}</span>

										<div className='flex-1'>
											<p className='text-sm font-medium text-neutral-800'>{title}</p>
											<p className='mt-1 text-xs text-neutral-500'>{description}</p>
										</div>

										{index < 5 && <span className='text-neutral-300'>↓</span>}
									</div>
								</div>
							))}
						</div>
					</div>
				</div>
			</section>

			{/* API KEY */}
			<section className='py-20'>
				<div className='mx-auto max-w-5xl px-6'>
					<div className='rounded-3xl border border-ai-100 bg-ai-50 p-8 md:p-10'>
						<div className='flex flex-col items-start gap-6 md:flex-row md:items-center'>
							<div className='flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-ai-100 text-2xl text-ai-500'>
								🔑
							</div>

							<div className='flex-1'>
								<h3 className='text-xl font-semibold text-neutral-800'>
									Conecta tu modelo de IA preferido
								</h3>

								<p className='mt-2 max-w-2xl text-sm leading-6 text-neutral-500'>
									Para utilizar KOSMO necesitas un API Key de un proveedor de modelos de
									IA. Tú eliges el modelo y mantienes el control sobre tu consumo.
								</p>
							</div>

							<div className='flex gap-3'>
								<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
									AI
								</div>
								<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
									✦
								</div>
								<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
									G
								</div>
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* CTA */}
			<section className='relative overflow-hidden border-t border-neutral-200 bg-gradient-to-r from-ai-500 to-ai-600 py-20'>
				<div className='absolute inset-0 bg-[radial-gradient(circle_at_50%_100%,rgba(255,255,255,0.15),transparent_40%)]' />

				<div className='relative mx-auto max-w-4xl px-6 text-center'>
					<h2 className='text-3xl font-bold text-neutral-0 md:text-4xl'>
						¿Listo para construir mejor software?
					</h2>

					<p className='mx-auto mt-5 max-w-2xl text-sm leading-6 text-ai-100'>
						Convierte tu idea en una aplicación real con la guía de la IA y la disciplina
						de Spec Driven Development.
					</p>

				<button
					onClick={openLoginModal}
					className='mt-8 rounded-xl bg-neutral-0 px-7 py-3.5 font-semibold text-ai-600 shadow-xl transition hover:-translate-y-0.5'
				>
					Comenzar ahora →
				</button>

					<p className='mt-5 text-xs text-ai-100'>
						Necesitas un API Key para comenzar.
					</p>
				</div>
			</section>

			{/* FOOTER */}
			<footer className='border-t border-neutral-200 bg-neutral-50'>
				<div className='mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 md:flex-row md:items-center md:justify-between'>
					<div className='flex items-center gap-3'>
						<div className='flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-ai-500 to-ai-600 text-sm font-bold text-neutral-0'>
							K
						</div>

						<span className='font-semibold text-neutral-800'>KOSMO</span>
					</div>

					<p className='text-xs text-neutral-500'>Spec Driven Development powered by AI.</p>

					<p className='text-xs text-neutral-400'>© 2026 KOSMO</p>
				</div>
			</footer>

			{/* AUTH MODAL */}
			{showAuthModal && (
				<div
					className='fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm'
					onClick={() => setShowAuthModal(false)}
				>
					<div
						className='relative w-full max-w-md mx-4 animate-slide-down'
						onClick={(e) => e.stopPropagation()}
					>
						{authView === 'login' ? (
							<Login
								onClose={() => setShowAuthModal(false)}
								onSwitchToRegister={() => setAuthView('register')}
							/>
						) : (
							<Register
								onClose={() => setShowAuthModal(false)}
								onSwitchToLogin={() => setAuthView('login')}
							/>
						)}
					</div>
				</div>
			)}
		</div>
	);
}
