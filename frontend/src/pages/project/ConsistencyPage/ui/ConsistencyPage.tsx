'use client';

import { applyConsistencyImpacts, useConsistencyStore } from '@/entities/consistency';
import type { DownstreamProposal } from '@/entities/consistency';
import { ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import { ConsistencyDiffCard } from './ConsistencyDiffCard';

const PHASE_LABELS: Record<string, string> = {
	features: 'Características',
	requirements: 'Requisitos',
	model: 'Modelo',
	discovery: 'Descubrimiento',
};

const RETURN_PATHS: Record<string, string> = {
	discovery: '/proyecto/descubrimiento',
	features: '/proyecto/caracteristicas',
	requirements: '/proyecto/requisitos',
	model: '/proyecto/modelo',
};

function groupByPhase(items: DownstreamProposal[]): [string, DownstreamProposal[]][] {
	const groups = new Map<string, DownstreamProposal[]>();
	for (const item of items) {
		const phase = item.phase || 'features';
		if (!groups.has(phase)) groups.set(phase, []);
		groups.get(phase)!.push(item);
	}
	return Array.from(groups.entries());
}

const ConsistencyPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const initializeProject = useAppStore((s) => s.initializeProject);

	const report = useConsistencyStore((s) => s.report);
	const rejectAll = useConsistencyStore((s) => s.rejectAll);
	const acceptAll = useConsistencyStore((s) => s.acceptAll);
	const acceptImpact = useConsistencyStore((s) => s.acceptImpact);
	const clearReport = useConsistencyStore((s) => s.clearReport);
	const undoImpact = useConsistencyStore((s) => s.undoImpact);

	const returnPath = report
		? (RETURN_PATHS[report.source_type] ?? '/proyecto/descubrimiento')
		: '/proyecto/descubrimiento';

	const [showConfirmLeave, setShowConfirmLeave] = useState(false);
	const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);
	const [applying, setApplying] = useState(false);
	const [showConfirmApply, setShowConfirmApply] = useState(false);

	const phaseGroups = useMemo(
		() => (report ? groupByPhase(report.downstream_impact) : []),
		[report],
	);

	if (!currentProject) {
		router.push('/proyecto');
		return null;
	}

	if (!report) {
		router.push(returnPath);
		return null;
	}

	const hasPending = report.downstream_impact.some((i) => i.accepted === undefined);

	const refreshProject = async () => {
		try {
			await initializeProject(currentProject.id);
		} catch {
			// non-blocking — the page will show what it can
		}
	};

	const handleBack = () => {
		if (hasPending) {
			setPendingNavigation(returnPath);
			setShowConfirmLeave(true);
		} else {
			router.push(returnPath);
		}
	};

	const handleConfirmLeave = () => {
		clearReport();
		setShowConfirmLeave(false);
		if (pendingNavigation) {
			router.push(pendingNavigation);
			setPendingNavigation(null);
		}
	};

	const handleCancelLeave = () => {
		setShowConfirmLeave(false);
		setPendingNavigation(null);
	};

	const handleAcceptAllBatch = async () => {
		if (!report || !currentProject) return;
		const selected = report.downstream_impact.filter((i) => i.accepted === true);
		if (selected.length === 0) return;
		setApplying(true);
		try {
			const result = await applyConsistencyImpacts(currentProject.id, selected);
			const failedCount = (result.failed || []).filter((f) => f.target_id).length;
			if (failedCount > 0) {
				toast.error(`${failedCount} de ${selected.length} cambios no se pudieron aplicar`);
			}
			if (failedCount < selected.length) {
				toast.success(`${selected.length - failedCount} cambios aplicados correctamente`);
				await refreshProject();
				clearReport();
				router.push(returnPath);
			}
		} catch {
			toast.error('No se pudieron aplicar los cambios');
		} finally {
			setApplying(false);
		}
	};

	const handleAcceptImpact = (impactId: string) => {
		acceptImpact(impactId);
	};

	const handleRejectImpact = (impactId: string) => {
		useConsistencyStore.getState().rejectImpact(impactId);
	};

	const handleMarkAll = () => {
		acceptAll();
	};

	const handleRejectAll = () => {
		rejectAll();
		clearReport();
		router.push(returnPath);
	};

	const handleApplyClick = () => {
		setShowConfirmApply(true);
	};

	const handleConfirmApply = () => {
		setShowConfirmApply(false);
		handleAcceptAllBatch();
	};

	const handleCancelApply = () => {
		setShowConfirmApply(false);
	};

	const selectedCount = report.downstream_impact.filter((i) => i.accepted === true).length;

	return (
		<>
			<div className='page-container gap-2'>
				<div className='page-header'>
					<h2 className='text-base-800 text-3xl font-bold'>Consistencia del Proyecto</h2>
					<p className='text-base-600 text-lg'>
						Revisa los cambios detectados entre fases de desarrollo, agrupados por
						nivel de impacto.
					</p>

					<div className='flex-1 min-h-0 mb-2'>
						<div className='flex h-full min-h-0 flex-col overflow-hidden bg-base-50 rounded'>
							<div className='flex shrink-0 items-center justify-between border-b border-base-300 bg-base-100 px-6 py-3'>
								<span className='text-sm font-semibold text-base-950'>
									{report.downstream_impact.length}{' '}
									{report.downstream_impact.length === 1 ? 'impacto detectado' : 'impactos detectados'}
								</span>
								<button
									type='button'
									onClick={handleBack}
									className='cursor-pointer rounded-md border border-base-300 bg-white px-4 py-1.5 text-sm font-medium text-base-950 transition-colors hover:bg-base-100 active:bg-base-200'
								>
									Volver
								</button>
							</div>

							<div className='flex-1 overflow-y-auto p-6 space-y-6'>
								{phaseGroups.map(([phase, items]) => (
									<div key={phase}>
										<h3 className='text-sm font-semibold text-base-500 uppercase tracking-wide mb-3'>
											{PHASE_LABELS[phase] || phase} ({items.length})
										</h3>
										{items.map((impact) => (
									<ConsistencyDiffCard
										key={impact.id}
										type='downstream_impact'
										item={impact}
										onAccept={
											impact.action !== 'delete' || impact.artifact_type === 'Feature'
												? () => handleAcceptImpact(impact.id)
												: undefined
										}
										onReject={
											impact.accepted !== true
												? () => handleRejectImpact(impact.id)
												: undefined
										}
										onUndo={
											impact.accepted !== undefined
												? () => undoImpact(impact.id)
												: undefined
										}
									/>
										))}
									</div>
								))}
							</div>

							<div className='flex shrink-0 items-center justify-between border-t border-base-300 bg-base-100 px-6 py-4'>
								<button
									type='button'
									onClick={handleRejectAll}
									className='cursor-pointer rounded-md border border-status-error bg-white px-5 py-2 text-sm font-medium text-status-error transition-colors hover:bg-status-error hover:text-white active:opacity-80'
								>
									Rechazar todos
								</button>
								<div className='flex items-center gap-3'>
									<button
										type='button'
										onClick={handleMarkAll}
										className='cursor-pointer rounded-md border border-base-300 bg-white px-5 py-2 text-sm font-medium text-base-950 transition-colors hover:bg-base-100 active:bg-base-200'
									>
										Marcar todos
									</button>
									<button
										type='button'
										onClick={handleApplyClick}
										disabled={selectedCount === 0 || applying}
										className='cursor-pointer rounded-md bg-status-success px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-status-success/90 active:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed'
									>
										{applying ? 'Aplicando...' : `Aplicar seleccionados (${selectedCount})`}
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			{showConfirmLeave && (
				<ModalConfirmLeave
					onCancel={handleCancelLeave}
					onConfirm={handleConfirmLeave}
					title='Cambios de consistencia pendientes'
					description='Si sale ahora, los cambios sugeridos no se aplicarán y no se volverán a mostrar. ¿Está seguro que desea salir?'
					cancelText='Cancelar'
					confirmText='Salir'
				/>
			)}

			{showConfirmApply && (
				<ModalConfirmLeave
					onCancel={handleCancelApply}
					onConfirm={handleConfirmApply}
					title='Aplicar cambios seleccionados'
					description={`Se aplicarán ${selectedCount} ${selectedCount === 1 ? 'cambio' : 'cambios'} sobre los artefactos downstream. Esta acción no se puede deshacer. ¿Desea continuar?`}
					cancelText='Cancelar'
					confirmText='Aplicar'
				/>
			)}
		</>
	);
};

export { ConsistencyPage };
