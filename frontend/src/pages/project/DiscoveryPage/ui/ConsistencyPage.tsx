'use client';

import { useConsistencyStore } from '@/entities/consistency';
import { ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useCallback, useRef, useState } from 'react';
import { ConsistencyDiffCard } from './ConsistencyDiffCard';

const ConsistencyPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);

	const report = useConsistencyStore((s) => s.report);
	const acceptAll = useConsistencyStore((s) => s.acceptAll);
	const rejectAll = useConsistencyStore((s) => s.rejectAll);
	const clearReport = useConsistencyStore((s) => s.clearReport);

	const [showConfirmLeave, setShowConfirmLeave] = useState(false);
	const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);

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

	const handleAcceptAll = () => {
		acceptAll();
		toast.success('Todos los cambios han sido aceptados');
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
						Revisa los cambios detectados entre fases de desarrollo. Acepta o rechaza cada
						propuesta para mantener la coherencia del proyecto.
					</p>

					<div className='flex-1 min-h-0 mb-2'>
						<div className='flex h-full min-h-0 flex-col overflow-hidden bg-base-50'>
							<div className='flex shrink-0 items-center justify-between border-b border-base-300 bg-base-100 px-6 py-3'>
								<div className='flex flex-1 items-center gap-2'>
									<span className='flex-1 text-center text-sm font-semibold text-base-950'>
										Actual
									</span>
									<div className='w-px self-stretch bg-base-300' />
									<span className='flex-1 text-center text-sm font-semibold text-base-950'>
										Propuesto ({report.downstream_impact.length}{' '}
										{report.downstream_impact.length === 1 ? 'impacto' : 'impactos'})
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

							<div className='flex min-h-0 flex-1 overflow-hidden'>
								<div
									ref={leftRef}
									onScroll={handleLeftScroll}
									className='flex-1 overflow-y-auto p-6 space-y-4'
								>
									{report.downstream_impact.map((impact) => (
										<ConsistencyDiffCard
											key={impact.id}
											type='downstream_impact'
											item={impact}
											side='left'
										/>
									))}
								</div>

								<div className='w-px shrink-0 bg-base-300' />

								<div
									ref={rightRef}
									onScroll={handleRightScroll}
									className='flex-1 overflow-y-auto p-6 space-y-4'
								>
									{report.downstream_impact.map((impact) => (
										<ConsistencyDiffCard
											key={impact.id}
											type='downstream_impact'
											item={impact}
											side='right'
										/>
									))}
								</div>
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
