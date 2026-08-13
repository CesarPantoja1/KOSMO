'use client';

import { applyConsistencyImpacts, useConsistencyStore } from '@/entities/consistency';
import type { DownstreamProposal } from '@/entities/consistency';
import { ModalConfirm, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useProjectStore } from '@/entities/project';
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
	const currentProject = useProjectStore((s) => s.currentProject);
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
				toast.error(
					`${failedCount} de ${selected.length} cambios no se pudieron aplicar`,
				);
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

	const selectedCount = report.downstream_impact.filter(
		(i) => i.accepted === true,
	).length;

	const pendingCount = report.downstream_impact.filter((i) => i.accepted === undefined).length;

	return (
		<>
			<div className='flex h-full min-h-0 flex-col bg-neutral-100'>
				{/* Barra superior */}
				<div className='flex shrink-0 items-center justify-between px-6 py-4 bg-neutral-0 border-b border-neutral-200'>
					<div className='flex items-center gap-4'>
						<h1 className='text-xl font-semibold text-neutral-800'>
							Revisión de consistencia
						</h1>
						{pendingCount > 0 && (
							<span className='px-3 py-1 text-sm font-medium rounded-full bg-warning-50 text-warning-700 border border-warning-200'>
								{pendingCount} {pendingCount === 1 ? 'cambio pendiente' : 'cambios pendientes'}
							</span>
						)}
					</div>
					<button type='button' onClick={handleBack} className='btn btn-secondary'>
						Volver
					</button>
				</div>

				{/* Contenido scrolleable */}
				<div className='flex-1 overflow-y-auto p-6'>
					<div className='max-w-4xl mx-auto space-y-6'>
						{phaseGroups.map(([phase, items]) => (
							<div key={phase} className='space-y-4'>
								<h3 className='text-sm font-semibold text-neutral-500 uppercase tracking-wide'>
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
				</div>

				{/* Barra inferior */}
				<div className='flex shrink-0 items-center justify-between px-6 py-4 bg-neutral-0 border-t border-neutral-200'>
					<button
						type='button'
						onClick={handleRejectAll}
						className='btn btn-destructive'
					>
						Rechazar todos
					</button>
					<div className='flex items-center gap-3'>
						<button
							type='button'
							onClick={handleMarkAll}
							className='btn btn-warning'
						>
							Marcar todos
						</button>
						<button
							type='button'
							onClick={handleApplyClick}
							disabled={selectedCount === 0 || applying}
							className='btn btn-primary'
						>
							{applying
								? 'Aplicando...'
								: `Aplicar seleccionados (${selectedCount})`}
						</button>
					</div>
				</div>
			</div>

			{showConfirmLeave && (
				<ModalConfirm
					onCancel={handleCancelLeave}
					onConfirm={handleConfirmLeave}
					title='Cambios de consistencia pendientes'
					description='Si sale ahora, los cambios sugeridos no se aplicarán y no se volverán a mostrar. ¿Está seguro que desea salir?'
					cancelText='Cancelar'
					confirmText='Salir'
				/>
			)}

			{showConfirmApply && (
				<ModalConfirm
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
