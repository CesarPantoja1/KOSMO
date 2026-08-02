'use client';

import {
	getCharacteristics,
	type Characteristic,
} from '@/entities/characteristic';
import { applyPlanChanges, discardPlan, usePlanStore, type PlanChange } from '@/entities/plan';
import {
	getRequirements,
	saveRequirements,
	useRequirementsStore,
} from '@/entities/requirements';
import { MarkdownDiff } from '@/feature';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

function buildProposal(original: string, charChanges: PlanChange[]): string {
	let result = original;
	for (const change of charChanges) {
		if (change.diff.before && result.includes(change.diff.before)) {
			result = result.replace(change.diff.before, change.diff.after);
		} else if (!change.diff.before && change.diff.after) {
			result += '\n\n' + change.diff.after;
		}
	}
	return result;
}

interface CharWithDiff {
	characteristic: Characteristic;
	originalMarkdown: string;
	proposedMarkdown: string;
	charChanges: PlanChange[];
}

export const PlanPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const clearPlan = usePlanStore((s) => s.clearPlan);
	const updatePlanChangeStatus = usePlanStore((s) => s.updatePlanChangeStatus);
	const setSelectedFeatureId = useRequirementsStore((s) => s.setSelectedFeatureId);

	const [items, setItems] = useState<CharWithDiff[]>([]);
	const [currentIndex, setCurrentIndex] = useState(0);
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
				const diffItems: CharWithDiff[] = [];

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

					const proposedContent = buildProposal(originalContent, charChanges);

					diffItems.push({
						characteristic: char,
						originalMarkdown: originalContent,
						proposedMarkdown: proposedContent,
						charChanges,
					});
				}

				setItems(diffItems);
			} catch {
				toast.error('Error al cargar la vista comparativa del plan');
			} finally {
				setIsLoading(false);
			}
		};

		loadData();
	}, [currentProject, router]);

	const currentItem = items[currentIndex] ?? null;

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
		if (!currentProject || !currentItem) return;
		setIsApplying(true);
		try {
			await saveRequirements(
				currentProject.id,
				currentItem.characteristic.id,
				currentItem.proposedMarkdown,
			);

			const changeIds = currentItem.charChanges.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, 'requirements', changeIds);

			if (result.failed_count > 0) {
				const reasons = result.failed_changes.map((f) => f.reason).join('. ');
				toast.error(`${result.failed_count} cambio(s) fallaron: ${reasons}`);
			} else {
				toast.success(`${result.applied_count} cambio(s) aplicados correctamente`);
			}

			for (const cid of changeIds) {
				updatePlanChangeStatus('requirements', cid, 'applied');
			}

			const next = currentIndex + 1;
			if (next < items.length) {
				setCurrentIndex(next);
			} else {
				clearPlan('requirements');
				setSelectedFeatureId(currentItem.characteristic.id);
				router.push('/proyecto/requisitos');
			}
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

	if (!currentItem) {
		return (
			<div className='page-container'>
				<div className='page-header'>
					<h2 className='text-base-800 text-3xl font-bold'>Requisitos EARS</h2>
					<p className='text-base-600 text-lg'>
						No hay cambios pendientes para revisar.
					</p>
				</div>
			</div>
		);
	}

	const label = items.length > 1
		? `${currentItem.characteristic.title} (${currentIndex + 1}/${items.length})`
		: currentItem.characteristic.title;

	return (
		<div className='page-container'>
			<div className='page-header'>
				<h2 className='text-base-800 text-3xl font-bold'>Requisitos EARS</h2>
				<p className='text-base-600 text-lg'>
					Revisa los cambios propuestos antes de aplicarlos — {label}
				</p>

				<div className='flex-1 min-h-0 mb-2'>
					<MarkdownDiff
						original={currentItem.originalMarkdown}
						proposal={currentItem.proposedMarkdown}
						originalLabel='Original'
						proposalLabel={`Propuesta (${currentItem.charChanges.length} ${currentItem.charChanges.length === 1 ? 'cambio' : 'cambios'})`}
						onBack={handleBack}
						onDiscard={isDiscarding ? () => {} : handleDiscard}
						onApply={isApplying ? () => {} : handleApply}
					/>
				</div>
			</div>
		</div>
	);
};
