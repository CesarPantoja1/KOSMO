'use client';

import { useDiscoveryStore } from '@/entities/discovery';
import type { ConsistencyReportResponse } from '@/entities/consistency';
import {
	ConsistencyProgress,
	useConsistencyStore,
	useConsistencyStream,
} from '@/entities/consistency';
import {
	applyPlanChanges,
	buildProposal,
	discardPlan,
	usePlanStore,
} from '@/entities/plan';
import { MarkdownDiff } from '@/feature';
import { toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export const PlanPage = () => {
	const router = useRouter();
	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const fetchAndHydratePlan = usePlanStore((s) => s.fetchAndHydratePlan);

	const {
		phases: streamPhases,
		isComplete,
		report: streamReport,
		error: streamError,
		start: startStream,
		phaseLabels,
	} = useConsistencyStream();

	const [originalMarkdown, setOriginalMarkdown] = useState('');
	const [isLoading, setIsLoading] = useState(true);
	const [isApplying, setIsApplying] = useState(false);
	const [isDiscarding, setIsDiscarding] = useState(false);
	const [isProcessing, setIsProcessing] = useState(false);

	const allChanges = planByPhase['discovery'] ?? [];
	const changes = allChanges.filter(
		(c) => c.status === 'pending' || c.status === 'added' || c.status === 'conflict',
	);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}
		useDiscoveryStore
			.getState()
			.getDiscovery(currentProject.id)
			.then((data) => setOriginalMarkdown(data.content))
			.catch(() => toast.error('Error al cargar el descubrimiento'))
			.finally(() => setIsLoading(false));
	}, [currentProject, router]);

	useEffect(() => {
		if (!isComplete || !streamReport) return;

		const downstream =
			(streamReport.downstream_impact as Array<Record<string, unknown>>) || [];
		const hasPending = downstream.some((i) => !i.accepted);

		const finish = async () => {
			if (currentProject) {
				await useDiscoveryStore.getState().getDiscovery(currentProject.id);
				await fetchAndHydratePlan(currentProject.id, 'discovery');
			}
			setIsProcessing(false);
			setIsApplying(false);

			if (hasPending) {
				useConsistencyStore
					.getState()
					.setReport(streamReport as unknown as ConsistencyReportResponse);
				router.push('/proyecto/descubrimiento/consistencia');
			} else {
				toast.info('No se detectaron cambios que afecten otras fases del proyecto');
				router.push('/proyecto/descubrimiento');
			}
		};

		finish().catch(() => router.push('/proyecto/descubrimiento'));
	}, [isComplete]); // eslint-disable-line react-hooks/exhaustive-deps

	useEffect(() => {
		if (!streamError) return;
		queueMicrotask(() => {
			setIsProcessing(false);
			setIsApplying(false);
			toast.error('Error al verificar la consistencia. Tus cambios no fueron aplicados.');
			router.push('/proyecto/descubrimiento');
		});
	}, [streamError]); // eslint-disable-line react-hooks/exhaustive-deps

	const proposalMarkdown = buildProposal(originalMarkdown, changes);

	const handleBack = () => {
		router.push('/proyecto/descubrimiento');
	};

	const handleDiscard = async () => {
		if (!currentProject) return;
		setIsDiscarding(true);
		try {
			await discardPlan(currentProject.id, 'discovery');
			usePlanStore.getState().clearPlan('discovery');
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
		setIsProcessing(true);

		try {
			const changeIds = changes.map((c) => c.id);
			const result = await applyPlanChanges(currentProject.id, 'discovery', changeIds);

			if (result.failed_count > 0) {
				const reasons = (result.failed_changes || [])
					.map((f) => f.reason)
					.filter(Boolean)
					.join(' ');
				setIsProcessing(false);
				setIsApplying(false);
				toast.error(
					`${result.failed_count} cambio(s) no se pudieron aplicar. ${reasons || 'Revisa el documento.'}`,
				);
				return;
			}
		} catch {
			setIsProcessing(false);
			setIsApplying(false);
			toast.error('Error al aplicar los cambios al documento');
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
			phaseOrigin: 'discovery',
			changes: changesToSend,
		});
	};

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
					<h2 className='text-base-800 text-3xl font-bold'>
						Descubrimiento del proyecto
					</h2>
					<p className='text-base-600 text-lg'>
						Revisa los cambios propuestos antes de aplicarlos al documento de
						descubrimiento.
					</p>

					<div className='flex-1 min-h-0 mb-2'>
						{isLoading ? (
							<div className='flex h-full items-center justify-center'>
								<div className='h-8 w-8 animate-spin rounded-full border-4 border-base-300 border-t-primary-100' />
							</div>
						) : (
							<MarkdownDiff
								original={originalMarkdown}
								proposal={proposalMarkdown}
								originalLabel='Original'
								proposalLabel={`Propuesta (${changes.length} ${changes.length === 1 ? 'cambio' : 'cambios'})`}
								onBack={handleBack}
								onDiscard={isDiscarding ? () => {} : handleDiscard}
								onApply={isApplying || isDiscarding ? () => {} : handleApply}
								processing={isApplying}
							/>
						)}
					</div>
				</div>
			</div>
		</>
	);
};
