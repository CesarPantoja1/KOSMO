'use client';

import { getDiscovery } from '@/entities/discovery';
import type { PlanChange } from '@/entities/plan';
import {
	applyPlanChanges,
	checkPlanCollision,
	discardPlan,
	usePlanStore,
} from '@/entities/plan';
import { MarkdownDiff } from '@/feature';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Construye el markdown propuesto aplicando todos los cambios al original en secuencia.
// Para cada cambio: si diff.before existe y se encuentra en el texto, lo reemplaza por diff.after.
// Si diff.before está vacío (cambio nuevo/adición), lo añade al final.
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

	const changes = planByPhase['discovery'] ?? [];

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
			// 1. Verificar colisiones antes de aplicar
			const collision = await checkPlanCollision(currentProject.id);
			if (collision.has_collision) {
				toast.error(
					`Hay ${collision.collisions.length} colisión(es) detectada(s). Resuelve los conflictos antes de aplicar.`,
				);
				setIsApplying(false);
				return;
			}

			// 2. Aplicar todos los cambios pendientes
			const changeIds = changes.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, changeIds);

			if (result.failed.length > 0) {
				toast.error(
					`${result.failed.length} cambio(s) no pudieron aplicarse. Los demás fueron aplicados correctamente.`,
				);
			} else {
				toast.success('Cambios aplicados correctamente');
			}

			clearPlan('discovery');
			router.push('/proyecto/descubrimiento');
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
			<div className='page-header flex-8/12'>
				<h2 className='text-base-800 text-3xl font-bold'>Descubrimiento del proyecto</h2>
				<p className='text-base-600 text-lg'>
					Revisa los cambios propuestos antes de aplicarlos al documento de
					descubrimiento.
				</p>

				<div className='w-full flex-1 min-h-0'>
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
