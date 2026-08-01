'use client';

import {
	getCharacteristics,
	type Characteristic,
} from '@/entities/characteristic';
import { applyPlanChanges, discardPlan, usePlanStore } from '@/entities/plan';
import {
	getRequirements,
	saveRequirements,
} from '@/entities/requirements';
import { MarkdownText, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

interface RequirementDiffItem {
	characteristic: Characteristic;
	originalMarkdown: string;
	proposedMarkdown: string;
}

function applyDiffToMarkdown(original: string, diffBefore: string, diffAfter: string): string {
	if (!original) return diffAfter;
	if (
		diffBefore &&
		diffBefore !== 'No especificado' &&
		diffBefore !== 'Ninguno' &&
		original.includes(diffBefore)
	) {
		return original.replace(diffBefore, diffAfter);
	}
	return `${original}\n\n${diffAfter}`;
}

function RequirementDiffCard({
	displayId,
	title,
	markdown,
}: {
	displayId: string;
	title: string;
	markdown: string;
}) {
	return (
		<div className='p-4 md:px-8 md:py-4 flex justify-start items-start gap-4 md:gap-7 transition-shadow outline outline-base-300 bg-white w-full max-w-full overflow-hidden rounded-sm'>
			<div className='w-12 md:w-14 flex flex-col text-xl font-bold justify-center my-auto items-center gap-2.5 shrink-0 text-black'>
				{displayId}
			</div>
			<div className='flex-1 flex flex-col justify-center gap-2.5 min-w-0 max-w-full overflow-hidden'>
				<h3 className='text-primary-100 text-xl font-semibold truncate'>{title}</h3>
				<div className='text-base-800 text-sm max-w-full overflow-hidden break-words'>
					<MarkdownText content={markdown || '_Sin requisitos cargados_'} />
				</div>
			</div>
		</div>
	);
}

export const PlanPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const clearPlan = usePlanStore((s) => s.clearPlan);

	const [items, setItems] = useState<RequirementDiffItem[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isApplying, setIsApplying] = useState(false);
	const [isDiscarding, setIsDiscarding] = useState(false);

	const allChanges = planByPhase['requirements'] ?? [];
	const changes = allChanges.filter(
		(c) => c.status === 'pending' || c.status === 'added' || c.status === 'conflict',
	);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const loadData = async () => {
			setIsLoading(true);
			try {
				const characteristics = await getCharacteristics(currentProject.id);
				const diffItems: RequirementDiffItem[] = [];

				for (const char of characteristics) {
					const charChanges = changes.filter((c) => c.context === char.id);
					if (charChanges.length === 0) continue;

					let originalContent = '';
					try {
						const reqRes = await getRequirements(currentProject.id, char.id);
						originalContent = reqRes.document_markdown || '';
					} catch {
						originalContent = '';
					}

					let proposedContent = originalContent;
					for (const change of charChanges) {
						proposedContent = applyDiffToMarkdown(
							proposedContent,
							change.diff.before,
							change.diff.after,
						);
					}

					diffItems.push({
						characteristic: char,
						originalMarkdown: originalContent,
						proposedMarkdown: proposedContent,
					});
				}

				setItems(diffItems);
			} catch (_err) {
				toast.error('Error al cargar la vista comparativa del plan');
			} finally {
				setIsLoading(false);
			}
		};

		loadData();
	}, [currentProject, router, changes.length]);

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
		router.push('/proyecto/requisitos');
	};

	const handleDiscard = async () => {
		if (!currentProject) return;
		setIsDiscarding(true);
		try {
			await discardPlan(currentProject.id, 'requirements');
			clearPlan('requirements');
			router.push('/proyecto/requisitos');
		} catch {
			toast.error('No se pudo descartar el plan');
		} finally {
			setIsDiscarding(false);
		}
	};

	const handleApply = async () => {
		if (!currentProject || changes.length === 0) return;
		setIsApplying(true);
		try {
			for (const item of items) {
				await saveRequirements(
					currentProject.id,
					item.characteristic.id,
					item.proposedMarkdown,
				);
			}

			const changeIds = changes.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, 'requirements', changeIds);

			if (result.failed_count > 0) {
				const reasons = result.failed_changes.map((f) => f.reason).join('. ');
				toast.error(`${result.failed_count} cambio(s) fallaron: ${reasons}`);
			} else {
				toast.success(`${result.applied_count} cambio(s) aplicados correctamente`);
			}

			clearPlan('requirements');
			router.push('/proyecto/requisitos');
		} catch {
			toast.error('Error al aplicar los cambios');
		} finally {
			setIsApplying(false);
		}
	};

	if (isLoading) {
		return (
			<div className='flex h-full items-center justify-center'>
				<div className='h-8 w-8 animate-spin rounded-full border-4 border-base-300 border-t-primary-100' />
			</div>
		);
	}

	return (
		<div className='page-container'>
			<div className='page-header'>
				<h2 className='text-base-800 text-3xl font-bold'>Requisitos EARS</h2>
				<p className='text-base-600 text-lg'>
					Revisa los cambios propuestos antes de aplicarlos a los requisitos del proyecto.
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
								className='flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-4'
							>
								{items.length === 0 ? (
									<p className='text-stone-500 text-sm text-center py-8'>
										No hay cambios pendientes para revisar.
									</p>
								) : (
									items.map((item) => (
										<RequirementDiffCard
											key={item.characteristic.id}
											displayId={item.characteristic.display_id}
											title={item.characteristic.title}
											markdown={item.originalMarkdown}
										/>
									))
								)}
							</div>

							{/* Divider */}
							<div className='w-px shrink-0 bg-base-300' />

							{/* Right — Proposal */}
							<div
								ref={rightRef}
								onScroll={handleRightScroll}
								className='flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-4'
							>
								{items.length === 0 ? (
									<p className='text-stone-500 text-sm text-center py-8'>
										No hay cambios pendientes para revisar.
									</p>
								) : (
									items.map((item) => (
										<RequirementDiffCard
											key={item.characteristic.id}
											displayId={item.characteristic.display_id}
											title={item.characteristic.title}
											markdown={item.proposedMarkdown}
										/>
									))
								)}
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
	);
};
