'use client';

import { useConsistencyStore } from '@/entities/consistency';
import { Close } from '@/shared/ui';
import { ConsistencyDiffCard } from './ConsistencyDiffCard';

const ConsistencyPage = () => {
	const report = useConsistencyStore((s) => s.report);
	const acceptChange = useConsistencyStore((s) => s.acceptChange);
	const rejectChange = useConsistencyStore((s) => s.rejectChange);
	const acceptImpact = useConsistencyStore((s) => s.acceptImpact);
	const rejectImpact = useConsistencyStore((s) => s.rejectImpact);
	const acceptAll = useConsistencyStore((s) => s.acceptAll);
	const rejectAll = useConsistencyStore((s) => s.rejectAll);
	const clearReport = useConsistencyStore((s) => s.clearReport);

	if (!report) return null;

	const hasPending =
		report.your_changes.some((c) => !c.accepted) ||
		report.downstream_impact.some((i) => !i.accepted);

	if (!hasPending) return null;

	return (
		<div className='fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-base-950/50 pt-10 pb-10'>
			<div className='flex w-full max-w-4xl flex-col rounded-xl bg-base-50 shadow-2xl'>
				<div className='flex items-center justify-between border-b border-base-300 px-6 py-4'>
					<div>
						<h1 className='text-xl font-bold text-base-800'>Consistencia del Proyecto</h1>
						<p className='mt-0.5 text-sm text-base-600'>
							Revisa los cambios detectados entre fases y acepta o rechaza cada uno.
						</p>
					</div>
					<button
						type='button'
						onClick={clearReport}
						className='cursor-pointer rounded-md p-2 text-base-600 transition-colors hover:bg-base-200 hover:text-base-800'
					>
						<Close color='' size={20} />
					</button>
				</div>

				<div className='flex-1 space-y-4 overflow-y-auto px-6 py-5'>
					{report.your_changes.length > 0 && (
						<section>
							<h2 className='mb-3 text-sm font-semibold uppercase tracking-wider text-base-600'>
								Tus cambios
							</h2>
							<div className='space-y-3'>
								{report.your_changes.map((change) => (
									<ConsistencyDiffCard
										key={change.change_id}
										type='your_change'
										item={change}
										onAccept={() => acceptChange(change.change_id)}
										onReject={() => rejectChange(change.change_id)}
									/>
								))}
							</div>
						</section>
					)}

					{report.downstream_impact.length > 0 && (
						<section>
							<h2 className='mb-3 text-sm font-semibold uppercase tracking-wider text-base-600'>
								Impacto en elementos descendientes
							</h2>
							<div className='space-y-3'>
								{report.downstream_impact.map((impact) => (
									<ConsistencyDiffCard
										key={impact.id}
										type='downstream_impact'
										item={impact}
										onAccept={() => acceptImpact(impact.id)}
										onReject={() => rejectImpact(impact.id)}
									/>
								))}
							</div>
						</section>
					)}
				</div>
			</div>
		</div>
	);
};

export default ConsistencyPage;
