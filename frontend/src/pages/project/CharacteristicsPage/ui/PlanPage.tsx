'use client';

import {
	getCharacteristics,
	type CharacteristicResponse,
} from '@/entities/characteristic';
import type { ConsistencyReportResponse } from '@/entities/consistency';
import {
	ConsistencyProgress,
	useConsistencyStore,
	useConsistencyStream,
} from '@/entities/consistency';
import type { PlanChange } from '@/entities/plan';
import { applyPlanChanges, discardPlan, usePlanStore } from '@/entities/plan';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

function buildProposal(
	original: CharacteristicResponse[],
	changes: PlanChange[],
): CharacteristicResponse[] {
	return original.map((c) => {
		let feature = { ...c };
		for (const change of changes) {
			if (change.context && change.context !== c.id) continue;
			const attribute = featureAttribute(change.section);
			if (attribute && change.diff.before && feature[attribute].includes(change.diff.before)) {
				feature = {
					...feature,
					[attribute]: feature[attribute].replace(change.diff.before, change.diff.after),
				};
			}
		}
		return feature;
	});
}

function featureAttribute(section: string): 'title' | 'description' | 'origin' | null {
	const normalized = section
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[^a-z]/g, '');
	if (normalized === 'titulo' || normalized === 'titulodelacaracteristica') return 'title';
	if (normalized === 'descripcion' || normalized === 'descripciondelacaracteristica') return 'description';
	if (normalized === 'origen' || normalized === 'origendelacaracteristica') return 'origin';
	return null;
}

function CharacteristicDiffCard({
	displayId,
	title,
	description,
}: {
	displayId: string;
	title: string;
	description: string;
}) {
	return (
		<div
			className={
				'm-0.5 px-8 py-4 inline-flex justify-start items-start gap-7 transition-shadow outline outline-base-300'
			}
		>
			<div className='w-14 inline-flex flex-col text-xl font-semibold justify-center my-auto items-center gap-2.5'>
				{displayId}
			</div>
			<div className='flex-1 inline-flex flex-col justify-center gap-2.5'>
				<h3 className='text-primary-100 text-xl font-semibold'>{title}</h3>
				<p className='feature-description-scroll text-base-800'>{description}</p>
			</div>
		</div>
	);
}

export const PlanPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const clearPlan = usePlanStore((s) => s.clearPlan);

	const [originalCharacteristics, setOriginalCharacteristics] = useState<
		CharacteristicResponse[]
	>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isApplying, setIsApplying] = useState(false);
	const [isDiscarding, setIsDiscarding] = useState(false);
	const [isProcessing, setIsProcessing] = useState(false);

	const {
		phases: streamPhases,
		isComplete,
		report: streamReport,
		error: streamError,
		start: startStream,
		phaseLabels,
	} = useConsistencyStream();

	const allChanges = planByPhase['features'] ?? [];
	const changes = allChanges.filter(
		(c) => c.status === 'pending' || c.status === 'added' || c.status === 'conflict',
	);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}
		getCharacteristics(currentProject.id)
			.then((data) => setOriginalCharacteristics(data))
			.catch(() => toast.error('Error al cargar las características'))
			.finally(() => setIsLoading(false));
	}, [currentProject, router]);

	useEffect(() => {
		if (!isComplete || !streamReport) return;

		const downstream = (streamReport.downstream_impact as Array<Record<string, unknown>>) || [];
		const hasPending = downstream.some((i) => !i.accepted);

		const finish = async () => {
			setIsProcessing(false);
			setIsApplying(false);

			if (hasPending) {
				useConsistencyStore.getState().setReport(
					streamReport as unknown as ConsistencyReportResponse,
				);
				toast.info(`${downstream.length} artefacto(s) en otras fases requieren revisión`);
			} else {
				toast.info('No se detectaron cambios que afecten otras fases del proyecto');
			}
			clearPlan('features');
			router.push('/proyecto/caracteristicas');
		};

		finish().catch(() => router.push('/proyecto/caracteristicas'));
	}, [isComplete]); // eslint-disable-line react-hooks/exhaustive-deps

	useEffect(() => {
		if (!streamError) return;
		queueMicrotask(() => {
			setIsProcessing(false);
			setIsApplying(false);
			toast.error('Error al verificar la consistencia. Tus cambios no fueron aplicados.');
			clearPlan('features');
			router.push('/proyecto/caracteristicas');
		});
	}, [streamError]); // eslint-disable-line react-hooks/exhaustive-deps

	const changedCharacteristics = originalCharacteristics.filter((c) =>
		changes.some(
			(change) =>
				change.context === c.id ||
				(!change.context &&
					change.diff.before &&
					[c.title, c.description, c.origin].some((value) => value.includes(change.diff.before))),
		),
	);

	const proposalCharacteristics = buildProposal(changedCharacteristics, changes);

	const leftRef = useRef<HTMLDivElement>(null);
	const rightRef = useRef<HTMLDivElement>(null);
	const isSyncingLeft = useRef(false);
	const isSyncingRight = useRef(false);

	const handleLeftScroll = useCallback(() => {
		if (isSyncingRight.current) return;
		const left = leftRef.current;
		const right = rightRef.current;
		if (!left || !right) return;
		isSyncingLeft.current = true;
		const ratio = left.scrollTop / (left.scrollHeight - left.clientHeight || 1);
		right.scrollTop = ratio * (right.scrollHeight - right.clientHeight);
		isSyncingLeft.current = false;
	}, []);

	const handleRightScroll = useCallback(() => {
		if (isSyncingLeft.current) return;
		const left = leftRef.current;
		const right = rightRef.current;
		if (!left || !right) return;
		isSyncingRight.current = true;
		const ratio = right.scrollTop / (right.scrollHeight - right.clientHeight || 1);
		left.scrollTop = ratio * (left.scrollHeight - left.clientHeight);
		isSyncingRight.current = false;
	}, []);

	const handleBack = () => {
		router.push('/proyecto/caracteristicas');
	};

	const handleDiscard = async () => {
		if (!currentProject) return;
		setIsDiscarding(true);
		try {
			await discardPlan(currentProject.id, 'features');
			clearPlan('features');
			router.push('/proyecto/caracteristicas');
		} catch {
			toast.error('No se pudo descartar el plan');
		} finally {
			setIsDiscarding(false);
		}
	};

	const handleApply = async () => {
		if (!currentProject || changes.length === 0) return;
		setIsApplying(true);
		setIsProcessing(true);

		try {
			const changeIds = changes.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, 'features', changeIds);

			if (result.failed_count > 0) {
				const reasons = (result.failed_changes || []).map((f) => f.reason).filter(Boolean).join(' ');
				setIsProcessing(false);
				setIsApplying(false);
				toast.error(
					`${result.failed_count} cambio(s) no se pudieron aplicar. ${reasons || 'Revisa las características.'}`,
				);
				return;
			}
		} catch {
			setIsProcessing(false);
			setIsApplying(false);
			toast.error('Error al aplicar los cambios a las características');
			return;
		}

		const changesToSend = changes.map((c) => ({
			section: c.section,
			diff_before: c.diff.before,
			diff_after: c.diff.after,
			description: c.description,
		}));

		startStream({
			projectId: currentProject.id,
			phaseOrigin: 'features',
			changes: changesToSend,
		});
	};

	if (isLoading) {
		return (
			<div className='flex h-full items-center justify-center'>
				<div className='h-8 w-8 animate-spin rounded-full border-4 border-base-300 border-t-primary-100' />
			</div>
		);
	}

	return (
		<>
			{isProcessing && (
				<ConsistencyProgress
					title='Verificando consistencia'
					description='La IA está analizando el impacto de los cambios en todas las fases del proyecto.'
					phases={streamPhases}
					phaseLabels={phaseLabels}
					isComplete={isComplete}
				/>
			)}

			<div className='page-container'>
			<div className='page-header'>
				<h2 className='text-base-800 text-3xl font-bold'>Características</h2>
				<p className='text-base-600 text-lg'>
					Revisa los cambios propuestos antes de aplicarlos a las características del
					proyecto.
				</p>

				<div className='flex-1 min-h-0 mb-2'>
					<div className='flex h-full min-h-0 flex-col overflow-hidden bg-base-50'>
						{/* Header */}
						<div className='flex shrink-0 items-center justify-between border-b border-base-300 bg-base-100 px-6 py-3'>
							<div className='flex flex-1 items-center gap-2'>
								<span className='flex-1 text-center text-sm font-semibold text-base-950'>
									Original
								</span>
								<div className='w-px self-stretch bg-base-300' />
								<span className='flex-1 text-center text-sm font-semibold text-base-950'>
									Propuesta ({changes.length}{' '}
									{changes.length === 1 ? 'cambio' : 'cambios'})
								</span>
							</div>
							<button
								type='button'
								onClick={handleBack}
								className='ml-6 cursor-pointer rounded-md border border-base-300 bg-white px-4 py-1.5 text-sm font-medium text-base-950 transition-colors hover:bg-base-100 active:bg-base-200'
							>
								Volver
							</button>
						</div>

						{/* Panels */}
						<div className='flex min-h-0 flex-1 overflow-hidden'>
							{/* Left — Original */}
							<div
								ref={leftRef}
								onScroll={handleLeftScroll}
								className='flex-1 overflow-y-auto p-6 space-y-4'
							>
								{changedCharacteristics.map((c) => (
									<CharacteristicDiffCard
										key={c.id}
										displayId={c.display_id}
										title={c.title}
										description={c.description}
									/>
								))}
							</div>

							{/* Divider */}
							<div className='w-px shrink-0 bg-base-300' />

							{/* Right */}
							<div
								ref={rightRef}
								onScroll={handleRightScroll}
								className='flex-1 overflow-y-auto p-6 space-y-4'
							>
								{proposalCharacteristics.map((c) => (
									<CharacteristicDiffCard
										key={c.id}
										displayId={c.display_id}
										title={c.title}
										description={c.description}
									/>
								))}
							</div>
						</div>

						{/* Footer */}
						<div className='flex shrink-0 items-center justify-between border-t border-base-300 bg-base-100 px-6 py-4'>
							<button
								type='button'
								onClick={handleDiscard}
								disabled={isDiscarding}
								className='cursor-pointer rounded-md border border-status-error bg-white px-5 py-2 text-sm font-medium text-status-error transition-colors hover:bg-status-error hover:text-white active:opacity-80 disabled:opacity-50'
							>
								{isDiscarding ? 'Descartando...' : 'Descartar Cambios'}
							</button>
							<button
								type='button'
								onClick={handleApply}
								disabled={isApplying || changes.length === 0}
								className='cursor-pointer rounded-md bg-primary-100 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-800 active:opacity-80 disabled:opacity-50'
							>
								{isApplying ? 'Aplicando...' : 'Aplicar Cambios'}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
		</>
	);
};
