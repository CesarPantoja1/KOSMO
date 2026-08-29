'use client';

import { useCharacteristicStore } from '@/entities/characteristic';
import type { ImplementationMetric } from '@/entities/implementation';
import { fetchPreviewUrl, useImplementationStore } from '@/entities/implementation';
import { useProjectStore, useProjectGithubRepo } from '@/entities/project';
import { GestionRepositorioGitHub } from '@/widgets';
import {
	AiOrbCenterIcon,
	CheckCircleWhiteIcon,
	EntitiesIcon,
	FlowIcon,
	InfoCircleIcon,
	PlusSmallIcon,
	RulesIcon,
	ScreensIcon,
	ShieldCheckIcon,
	SmallCheckIcon,
	SparkleIcon,
	StarIcon,
} from '@/shared/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const iconMap: Record<ImplementationMetric['icon'], React.ReactNode> = {
	screens: <ScreensIcon color='text-ai-600' />,
	entities: <EntitiesIcon color='text-primary-600' />,
	rules: <RulesIcon color='text-warning-600' />,
	integrations: <StarIcon color='text-primary-600' />,
	validations: <ShieldCheckIcon color='text-info-700' />,
	actions: <FlowIcon color='text-ai-600' />,
};

const ImplementationSummaryPage = () => {
	const router = useRouter();
	const summary = useImplementationStore((s) => s.summary);
	const [previewUrl, setPreviewUrl] = useState<string | null>(null);
	const [previewLoading, setPreviewLoading] = useState(false);

	const currentProjectId = useProjectStore((s) => s.currentProject?.id ?? null);
	const github = useProjectGithubRepo(currentProjectId);

	const loadImplementation = useImplementationStore((s) => s.loadImplementation);
	const selectedCharacteristic = useCharacteristicStore(
		(s) => s.currentCharacteristics.find((c) => c.id === s.selectedId) ?? null,
	);

	// Si el resumen no está en el store (recarga de página), se reconstruye desde el servidor.
	useEffect(() => {
		if (summary || !selectedCharacteristic) return;
		loadImplementation(
			selectedCharacteristic.id,
			selectedCharacteristic.title,
			selectedCharacteristic.display_id,
		);
	}, [summary, selectedCharacteristic, loadImplementation]);

	// La vista previa es por proyecto (un puerto propio): se consulta al backend.
	useEffect(() => {
		const project = useProjectStore.getState().currentProject;
		if (!project) return;
		let cancelled = false;
		fetchPreviewUrl(project.id)
			.then((url) => {
				if (!cancelled) setPreviewUrl(url);
			})
			.catch(() => {
				if (!cancelled) setPreviewUrl(null);
			})
			.finally(() => {
if (!cancelled) setPreviewLoading(false);
	});
	return () => {
		cancelled = true;
	};
	}, []);

	if (!summary) {
		return (
			<section className='page-container'>
				<div className='flex flex-col items-center justify-center min-h-[60vh] gap-4'>
					<p className='text-neutral-500'>No hay resumen disponible.</p>
					<Link href='/proyecto/codigo' className='btn btn-secondary'>
						Volver a Implementación
					</Link>
				</div>
			</section>
		);
	}

	return (
		<section className='page-container'>
			<div className='page-header'>
				{currentProjectId && (
					<div className='mb-4'>
						<GestionRepositorioGitHub
							viewState={github.viewState}
							status={github.status}
							loading={github.loading}
							error={github.error}
							onCreate={async (input) => {
								await github.createRepo(input);
							}}
							onSync={async () => {
								await github.sync();
							}}
						/>
					</div>
				)}

				<div className='flex items-start justify-between gap-4'>
					<div className='flex flex-col gap-1'>
						<h1 className='text-neutral-800 text-lg md:text-xl font-bold'>
							Resumen de implementación
						</h1>
						<p className='text-neutral-500 text-sm md:text-base'>
							Estos son los elementos que forman parte de tu proyecto.
						</p>
					</div>
					<button onClick={() => router.back()} className='btn btn-secondary shrink-0'>
						Volver
					</button>
				</div>

				<div className='grid lg:grid-cols-2 gap-6 mt-6'>
					<div className='flex flex-col gap-6'>
						<div className='grid grid-cols-2 gap-3'>
							{summary.metrics.map((metric) => (
								<div
									key={metric.label}
									className='rounded-lg border border-neutral-100 bg-neutral-50 p-4'
								>
									<div
										className={`mb-3 flex h-9 w-9 items-center justify-center rounded-md ${metric.iconBg}`}
									>
										{iconMap[metric.icon]}
									</div>
									<p className='text-2xl font-bold text-neutral-900'>{metric.value}</p>
									<p className='mt-1 text-xs text-neutral-500'>{metric.label}</p>
								</div>
							))}
						</div>

						<div>
							<h3 className='mb-3 text-sm font-semibold text-neutral-800'>Tecnologías</h3>
							<div className='flex flex-wrap gap-2'>
								{summary.technologies.map((t) => (
									<span
										key={t}
										className='rounded-full bg-neutral-100 px-3 py-1.5 text-xs font-medium text-neutral-700'
									>
										{t}
									</span>
								))}
							</div>
						</div>

						<div>
							<h3 className='mb-3 text-sm font-semibold text-neutral-800'>
								¿Qué puedes hacer ahora?
							</h3>
							<div className='space-y-3'>
								{summary.nextSteps.map((step) => (
									<div key={step} className='flex items-start gap-3'>
										<div className='mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success-50'>
											<SmallCheckIcon color='text-success-700' />
										</div>
										<p className='text-sm text-neutral-600'>{step}</p>
									</div>
								))}
							</div>
						</div>
					</div>

					<div className='flex flex-col items-center justify-center gap-6 rounded-xl bg-ai-50/40 border border-neutral-200 p-8'>
						<div className='relative mx-auto flex h-36 w-36 items-center justify-center'>
							<div className='absolute inset-4 rounded-2xl bg-ai-100' />
							<div className='relative flex h-20 w-20 items-center justify-center rounded-xl border-2 border-ai-500 bg-neutral-0 shadow-2'>
								<AiOrbCenterIcon size={40} color='text-ai-600' />
							</div>
							<div className='absolute right-1 top-1 flex h-10 w-10 items-center justify-center rounded-full bg-success-500 shadow-2'>
								<CheckCircleWhiteIcon size={20} color='text-neutral-0' />
							</div>
							<div className='absolute left-0 top-4 text-ai-500'>
								<SparkleIcon size={20} />
							</div>
							<div className='absolute bottom-3 right-0 text-ai-500'>
								<SparkleIcon size={16} />
							</div>
						</div>

						<div className='text-center'>
							<h3 className='text-lg font-bold text-neutral-900'>
								¡Tu aplicación está lista!
							</h3>
							<p className='mx-auto mt-2 max-w-xs text-sm text-neutral-500'>
								Hemos generado la estructura y lógica de tu proyecto a partir de todo lo
								que definiste en KOSMO.
							</p>
							{previewLoading ? (
								<button type='button' disabled className='btn btn-primary mt-4'>
									Preparando vista previa...
								</button>
							) : previewUrl ? (
								<a
									href={previewUrl}
									target='_blank'
									rel='noopener noreferrer'
									className='btn btn-primary mt-4'
								>
									Ver aplicación
								</a>
							) : (
								<button type='button' disabled className='btn btn-primary mt-4'>
									Vista previa no disponible
								</button>
							)}
						</div>

						<div className='w-full rounded-lg border border-ai-100 bg-neutral-0 p-4 text-left'>
							<div className='flex gap-3'>
								<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-ai-50'>
									<InfoCircleIcon size={16} color='text-ai-600' />
								</div>
								<div>
									<p className='text-sm font-semibold text-neutral-800'>
										¿Qué hemos generado?
									</p>
									<p className='mt-1 text-xs leading-5 text-neutral-500'>
										La estructura, datos, reglas y lógica necesarios para que puedas
										continuar construyendo tu aplicación.
									</p>
								</div>
							</div>
						</div>

						<div className='w-full rounded-lg border border-primary-100 bg-primary-50 p-4 text-left'>
							<div className='flex gap-3'>
								<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-100'>
									<PlusSmallIcon size={16} color='text-primary-600' />
								</div>
								<div>
									<p className='text-sm font-semibold text-primary-900'>
										No necesitas escribir código
									</p>
									<p className='mt-1 text-xs leading-5 text-primary-900/70'>
										KOSMO se encarga de la parte técnica para que puedas enfocarte en tu
										aplicación.
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	);
};

export { ImplementationSummaryPage };
