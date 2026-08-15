'use client';

import { useConsistencyGateStore, CONSISTENCY_REVIEW_ROUTES } from '@/entities/consistency';
import type { ConsistencyTargetPhase, ReviewCard } from '@/entities/consistency';
import { useProjectStore } from '@/entities/project';
import { useCharacteristicStore } from '@/entities/characteristic';
import { useRequirementsStore } from '@/entities/requirements';
import { useModelingStore } from '@/entities/modeling';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { preloadPlantUmlEngine } from '@/feature/plantuml-viewer/lib/engine-loader';
import { ArrowLeft, ModalConfirm, toast } from '@/shared/ui';
import { formatApiError } from '@/shared/api';
import { GateReviewCard } from './GateReviewCard';

const TARGET_LABELS: Record<ConsistencyTargetPhase, string> = {
	features: 'Características',
	requirements: 'Requisitos',
	model: 'Modelo',
};

const ROUTE_TO_TARGET: Record<string, ConsistencyTargetPhase> = {
	caracteristicas: 'features',
	requisitos: 'requirements',
	modelo: 'model',
	descubrimiento: 'features',
};

const TARGET_TO_ROUTE: Record<ConsistencyTargetPhase, string> = {
	features: '/proyecto/caracteristicas',
	requirements: '/proyecto/requisitos',
	model: '/proyecto/modelo',
};

const ACTIVITY_LABELS: Record<string, string> = {
	applied: 'Aplicado',
	discarded: 'Descartado',
	failed: 'Falló',
	evaluating: 'Evaluando',
	completed: 'Pendiente',
};

const refreshArtifactStores = async (projectId: string, cards: ReviewCard[]) => {
	const fetches: Promise<unknown>[] = [
		useCharacteristicStore.getState().getCharacteristics(projectId),
	];
	for (const card of cards) {
		const featureId = card.target_artifact_id.split(':')[0];
		if (card.artifact_type === 'EARSRequirement') {
			fetches.push(useRequirementsStore.getState().getRequirements(projectId, featureId));
		} else if (card.artifact_type === 'ActivityDiagram') {
			fetches.push(useModelingStore.getState().getDiagram(projectId, featureId));
		}
	}
	await Promise.allSettled(fetches);
};

const ConsistencyPage = () => {
	const router = useRouter();
	const params = useParams<{ fase?: string }>();
	const targetPhase: ConsistencyTargetPhase =
		ROUTE_TO_TARGET[params?.fase ?? ''] ?? 'features';

	const currentProject = useProjectStore((s) => s.currentProject);

	const status = useConsistencyGateStore((s) => s.status);
	const reviewLoading = useConsistencyGateStore((s) => s.reviewLoading);
	const cardsByPhase = useConsistencyGateStore((s) => s.cardsByPhase);
	const actionByEvaluation = useConsistencyGateStore((s) => s.actionByEvaluation);
	const activity = useConsistencyGateStore((s) => s.activity);
	const loadStatus = useConsistencyGateStore((s) => s.loadStatus);
	const loadReview = useConsistencyGateStore((s) => s.loadReview);
	const applyEvaluation = useConsistencyGateStore((s) => s.applyEvaluation);
	const discardEvaluation = useConsistencyGateStore((s) => s.discardEvaluation);
	const bulkResolve = useConsistencyGateStore((s) => s.bulkResolve);
	const loadActivity = useConsistencyGateStore((s) => s.loadActivity);

	const [confirmBulk, setConfirmBulk] = useState<'apply' | 'discard' | null>(null);

	const cards: ReviewCard[] = cardsByPhase[targetPhase] ?? [];
	const phaseStatus = status?.phases?.[targetPhase];
	const evaluating = phaseStatus?.evaluating ?? 0;
	const pending = phaseStatus?.pending ?? 0;

	useEffect(() => {
		preloadPlantUmlEngine();
	}, []);

	useEffect(() => {
		if (!currentProject) return;
		const timer = window.setTimeout(() => {
			void loadStatus(currentProject.id).catch(() => undefined);
			void loadReview(currentProject.id, targetPhase).catch(() => undefined);
			void loadActivity(currentProject.id).catch(() => undefined);
		}, 0);
		return () => window.clearTimeout(timer);
	}, [currentProject, targetPhase, loadStatus, loadReview, loadActivity]);

	if (!currentProject) {
		router.push('/proyecto');
		return null;
	}

	const reload = async () => {
		await Promise.all([
			loadStatus(currentProject.id),
			loadReview(currentProject.id, targetPhase),
			loadActivity(currentProject.id),
		]);
	};

	const handleApply = async (card: ReviewCard) => {
		try {
			await applyEvaluation(currentProject.id, targetPhase, card.evaluation_id);
			toast.success('Cambio aplicado');
			await reload();
			await refreshArtifactStores(currentProject.id, [card]);
		} catch (err) {
			toast.error(formatApiError(err, 'No se pudo aplicar el cambio.'));
			await reload();
		}
	};

	const handleDiscard = async (card: ReviewCard) => {
		try {
			await discardEvaluation(currentProject.id, targetPhase, card.evaluation_id);
			toast.success('Sugerencia descartada');
			await reload();
		} catch (err) {
			toast.error(formatApiError(err, 'No se pudo descartar la sugerencia.'));
			await reload();
		}
	};

	const handleBulk = async () => {
		if (!confirmBulk) return;
		const action = confirmBulk;
		setConfirmBulk(null);
		try {
			const result = await bulkResolve(currentProject.id, action, targetPhase);
			toast.success(
				`${result.resolved} sugerencia(s) ${action === 'apply' ? 'aplicada(s)' : 'descartada(s)'}${
					result.skipped > 0 ? ` · ${result.skipped} obsoleta(s) re-evaluándose` : ''
				}`,
			);
			await reload();
			await refreshArtifactStores(currentProject.id, cards);
		} catch (err) {
			toast.error(formatApiError(err, 'No se pudo completar la operación.'));
			await reload();
		}
	};

	const phaseLabel = TARGET_LABELS[targetPhase];

	return (
		<>
			{confirmBulk && (
				<ModalConfirm
					title={confirmBulk === 'apply' ? 'Aplicar todas las sugerencias' : 'Descartar todas las sugerencias'}
					description={
						confirmBulk === 'apply'
							? `Se aplicarán todas las sugerencias frescas de ${phaseLabel}. Los cambios se encadenarán hacia las fases siguientes.`
							: `Se descartarán todas las sugerencias frescas de ${phaseLabel}. Si la fuente vuelve a cambiar, aparecerán sugerencias nuevas.`
					}
					cancelText='Cancelar'
					confirmText={confirmBulk === 'apply' ? 'Aplicar todas' : 'Descartar todas'}
					onCancel={() => setConfirmBulk(null)}
					onConfirm={handleBulk}
				/>
			)}

			<div className='page-container flex-col gap-4'>
				<div className='page-header shrink-0'>
					<div className='flex flex-col gap-2'>
						<Link
							href={TARGET_TO_ROUTE[targetPhase]}
							className='flex w-fit items-center gap-1 text-sm font-medium text-neutral-500 hover:text-neutral-700'
						>
							<ArrowLeft size={16} color='' />
							Volver a {phaseLabel}
						</Link>
						<h2 className='text-neutral-800 text-3xl font-bold'>
							Revisión de consistencia
						</h2>
						<p className='text-neutral-500 text-base'>
							El agente detectó impactos de cambios sobre {phaseLabel}. Revisa cada
							sugerencia antes de aplicarla.
						</p>
					</div>
				</div>

				{/* Selector de fase destino */}
				<div className='flex shrink-0 items-center gap-2'>
					{(Object.keys(TARGET_LABELS) as ConsistencyTargetPhase[]).map((phase) => (
						<Link
							key={phase}
							href={CONSISTENCY_REVIEW_ROUTES[phase]}
							className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
								phase === targetPhase
									? 'bg-primary-500 text-neutral-0'
									: 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
							}`}
						>
							{TARGET_LABELS[phase]}
						</Link>
					))}
				</div>

				{evaluating > 0 && (
					<div
						role='status'
						className='flex shrink-0 items-center gap-2 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3'
					>
						<span className='h-2 w-2 animate-pulse rounded-full bg-warning-500' />
						<p className='text-sm text-warning-700'>
							El agente está evaluando impactos sobre {phaseLabel}. Los resultados
							aparecerán aquí al terminar.
						</p>
					</div>
				)}

				{!reviewLoading && cards.length > 0 && (
					<div className='flex shrink-0 items-center justify-between gap-2'>
						<p className='text-sm text-neutral-500'>
							{pending} sugerencia(s) pendiente(s) de decisión
						</p>
						<div className='flex items-center gap-2'>
							<button
								type='button'
								onClick={() => setConfirmBulk('discard')}
								className='btn btn-secondary btn-sm'
							>
								Descartar todas
							</button>
							<button
								type='button'
								onClick={() => setConfirmBulk('apply')}
								className='btn btn-primary btn-sm'
							>
								Aplicar todas
							</button>
						</div>
					</div>
				)}

				{/* Cards y actividad */}
				<div className='flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto'>
					{reviewLoading && cards.length === 0 && (
						<div className='flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-0 px-4 py-6'>
							<p className='text-sm text-neutral-400'>Cargando sugerencias…</p>
						</div>
					)}

					{!reviewLoading && cards.length === 0 && evaluating === 0 && (
						<div className='flex flex-col items-center gap-3 rounded-lg border border-neutral-200 bg-neutral-0 px-8 py-12 text-center'>
							<h3 className='text-lg font-semibold text-neutral-800'>
								Todo consistente en {phaseLabel}
							</h3>
							<p className='max-w-md text-sm leading-6 text-neutral-500'>
								No hay sugerencias pendientes para esta fase. Si aún no generaste los
								artefactos de {phaseLabel}, el análisis se completará cuando existan.
							</p>
						</div>
					)}

					{cards.map((card) => (
						<GateReviewCard
							key={card.evaluation_id}
							card={card}
							busy={Boolean(actionByEvaluation[card.evaluation_id])}
							onApply={() => void handleApply(card)}
							onDiscard={() => void handleDiscard(card)}
						/>
					))}

					{/* Actividad (progressive disclosure) */}
					<details className='group rounded-lg border border-neutral-200 bg-neutral-0'>
						<summary className='cursor-pointer list-none px-4 py-3 text-sm font-medium text-neutral-600 hover:bg-neutral-50'>
							Actividad reciente {activity && activity.length > 0 ? `(${activity.length})` : ''}
						</summary>
						<div className='flex flex-col gap-2 border-t border-neutral-200 px-4 py-3'>
							{(!activity || activity.length === 0) && (
								<p className='text-sm text-neutral-400'>Sin actividad registrada.</p>
							)}
							{activity?.map((item) => (
								<div
									key={item.evaluation_id}
									className='flex items-start justify-between gap-3 text-sm'
								>
									<div className='min-w-0'>
										<p className='truncate font-medium text-neutral-700'>
											{item.target_title || item.target_artifact_id}
										</p>
										{item.failure_reason && (
											<p className='truncate text-xs text-neutral-400'>
												{item.failure_reason}
											</p>
										)}
									</div>
									<div className='flex shrink-0 items-center gap-2'>
										<span className='rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600'>
											{ACTIVITY_LABELS[item.status] ?? item.status}
										</span>
										<span className='text-xs text-neutral-400'>
											{new Date(item.updated_at).toLocaleString()}
										</span>
									</div>
								</div>
							))}
						</div>
					</details>
				</div>
			</div>
		</>
	);
};

export { ConsistencyPage };
