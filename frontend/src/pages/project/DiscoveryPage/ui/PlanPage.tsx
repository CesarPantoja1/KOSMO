'use client';

import { getDiscovery } from '@/entities/discovery';
import { checkConsistency, useConsistencyStore } from '@/entities/consistency';
import type { PlanChange } from '@/entities/plan';
import {
	applyPlanChanges,
	discardPlan,
	usePlanStore,
} from '@/entities/plan';
import { MarkdownDiff } from '@/feature';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

function buildProposal(original: string, changes: PlanChange[]): string {
	let result = original;
	for (const change of changes) {
		if (change.diff.before && result.includes(change.diff.before)) {
			result = result.replace(change.diff.before, change.diff.after);
		} else if (!change.diff.before && change.diff.after) {
			result += '\n\n' + change.diff.after;
		}
	}
	return result;
}

export const PlanPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const clearPlan = usePlanStore((s) => s.clearPlan);

	const [originalMarkdown, setOriginalMarkdown] = useState('');
	const [isLoading, setIsLoading] = useState(true);
	const [isApplying, setIsApplying] = useState(false);
	const [isDiscarding, setIsDiscarding] = useState(false);

	const allChanges = planByPhase['discovery'] ?? [];
	const changes = allChanges.filter(
		(c) => c.status === 'pending' || c.status === 'added' || c.status === 'conflict',
	);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}
		getDiscovery(currentProject.id)
			.then((data) => setOriginalMarkdown(data.content))
			.catch(() => toast.error('Error al cargar el descubrimiento'))
			.finally(() => setIsLoading(false));
	}, [currentProject, router]);

	const proposalMarkdown = buildProposal(originalMarkdown, changes);

	const handleBack = () => {
		router.push('/proyecto/descubrimiento');
	};

	const handleDiscard = async () => {
		if (!currentProject) return;
		setIsDiscarding(true);
		try {
			await discardPlan(currentProject.id, 'discovery');
			clearPlan('discovery');
			router.push('/proyecto/descubrimiento');
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
			const changeIds = changes.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, 'discovery', changeIds);

			if (result.failed_count > 0) {
				const reasons = result.failed_changes
					.map((f) => f.reason)
					.join('. ');
				toast.error(
					`${result.failed_count} cambio(s) fallaron: ${reasons}`,
				);
			} else {
				toast.success(`${result.applied_count} cambio(s) aplicados correctamente`);
			}

			const changesToSend = changes.map((c) => ({
				section: c.section,
				diff_before: c.diff.before,
				diff_after: c.diff.after,
			}));

			clearPlan('discovery');
			router.push('/proyecto/descubrimiento');

			checkConsistency({
				project_id: currentProject.id,
				phase_origin: 'discovery',
				phase_destination: 'features',
				changes: changesToSend,
			})
				.then((report) => {
					useConsistencyStore.getState().setReport(report);
				})
				.catch(() => {
					toast.error('Error al verificar consistencia');
				});
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
				<h2 className='text-base-800 text-3xl font-bold'>Descubrimiento del proyecto</h2>
				<p className='text-base-600 text-lg'>
					Revisa los cambios propuestos antes de aplicarlos al documento de
					descubrimiento.
				</p>

				<div className='flex-1 min-h-0 mb-2'>
					<MarkdownDiff
						original={originalMarkdown}
						proposal={proposalMarkdown}
						originalLabel='Original'
						proposalLabel={`Propuesta (${changes.length} ${changes.length === 1 ? 'cambio' : 'cambios'})`}
						onBack={handleBack}
						onDiscard={isDiscarding ? () => {} : handleDiscard}
						onApply={isApplying ? () => {} : handleApply}
					/>
				</div>
			</div>
		</div>
	);
};
