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
	const clearReport = useConsistencyStore((s) => s.clearReport);
	const undoImpact = useConsistencyStore((s) => s.undoImpact);

	const [showConfirmLeave, setShowConfirmLeave] = useState(false);
	const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);
	const [acceptingId, setAcceptingId] = useState<string | null>(null);

	const phaseGroups = useMemo(
		() => (report ? groupByPhase(report.downstream_impact) : []),
		[report],
	);

	if (!currentProject) {
		router.push('/proyecto');
		return null;
	}

	if (!report) {
		router.push('/proyecto/descubrimiento');
		return null;
	}

	const hasPending = report.downstream_impact.some((i) => !i.accepted);

	if (!hasPending) {
		clearReport();
		router.push('/proyecto/descubrimiento');
		return null;
	}

	const refreshProject = async () => {
		try {
			await initializeProject(currentProject.id);
		} catch {
			// non-blocking — the page will show what it can
		}
	};

	const handleBack = () => {
		if (hasPending) {
			setPendingNavigation('/proyecto/descubrimiento');
			setShowConfirmLeave(true);
		} else {
			router.push('/proyecto/descubrimiento');
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

	const handleAcceptAll = async () => {
		if (!report || !currentProject) return;
		const pending = report.downstream_impact.filter((i) => !i.accepted);
		if (pending.length === 0) {
			clearReport();
			router.push('/proyecto/descubrimiento');
			return;
		}
		try {
			const result = await applyConsistencyImpacts(currentProject.id, pending);
			const failedCount = (result.failed || []).filter((f) => f.target_id).length;
			if (failedCount > 0) {
				toast.error(`${failedCount} de ${pending.length} cambios no se pudieron aplicar`);
			} else {
				toast.success(`${pending.length} cambios aplicados correctamente`);
			}
			if (failedCount < pending.length) {
				await refreshProject();
			}
		} catch {
			toast.error('No se pudieron aplicar los cambios');
		} finally {
			clearReport();
			router.push('/proyecto/descubrimiento');
		}
	};

	const handleAcceptImpact = async (impactId: string) => {
		if (!report || !currentProject) return;
		const impact = report.downstream_impact.find((i) => i.id === impactId);
		if (!impact) return;
		setAcceptingId(impactId);
		try {
			await applyConsistencyImpacts(currentProject.id, [impact]);
			useConsistencyStore.getState().acceptImpact(impactId);
			toast.success('Cambio aplicado correctamente');
			await refreshProject();
		} catch {
			toast.error('No se pudo aplicar el cambio');
		} finally {
			setAcceptingId(null);
		}
	};

	const handleRejectImpact = (impactId: string) => {
		useConsistencyStore.getState().rejectImpact(impactId);
	};

	const handleRejectAll = () => {
		rejectAll();
		toast.success('Todos los cambios han sido descartados');
	};

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
											!impact.accepted
												? () => handleRejectImpact(impact.id)
												: undefined
										}
										onUndo={
											impact.accepted !== undefined
												? () => undoImpact(impact.id)
												: undefined
										}
										accepting={acceptingId === impact.id}
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
								<button
									type='button'
									onClick={handleAcceptAll}
									className='cursor-pointer rounded-md bg-status-success px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-status-success/90 active:opacity-80'
								>
									Aceptar todos
								</button>
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
		</>
	);
};

export { ConsistencyPage };
