'use client';

import { deletePlanChange, usePlanStore } from '@/entities/plan';
import { ArrowRight, toast } from '@/shared/ui';
import Trash from '@/shared/ui/icons/Trash';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { ChevronIcon } from './icon/ChevronIcon';

interface Props {
	phase: string;
	navigateTo: string;
	contextId?: string | null;
}

export function FloatingPlan({ phase, navigateTo, contextId }: Props) {
	const [open, setOpen] = useState(false);
	const router = useRouter();

	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const removeFromPlan = usePlanStore((s) => s.removeFromPlan);

	const allItems = planByPhase[phase] ?? [];
	const items = allItems.filter(
		(c) =>
			(c.status === 'pending' || c.status === 'added' || c.status === 'conflict') &&
			(!contextId || c.context === contextId),
	);

	if (items.length === 0) return null;

	const handleRemove = async (changeId: string) => {
		if (!currentProject) return;
		removeFromPlan(phase, changeId);
		try {
			await deletePlanChange(currentProject.id, phase, changeId);
		} catch (err) {
			console.warn('[FloatingPlan] Error al eliminar cambio:', err);
			toast.error('No se pudo eliminar el cambio del plan');
		}
	};

	const handleNavigateToPlan = () => {
		router.push(navigateTo);
	};

	return (
		<div className='absolute bottom-6 right-2 z-50 flex flex-col items-end gap-2'>
			{open && (
				<div className='w-80 overflow-hidden rounded-xl border border-base-300 bg-base-50 shadow-[0_8px_24px_rgba(0,0,0,0.12)]'>
					<div className='flex items-center justify-between border-b border-base-300 bg-base-100 px-4 py-3'>
						<span className='text-xs font-semibold uppercase tracking-wide text-base-600'>
							Cambios pendientes
						</span>
						<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-100 px-1.5 text-xs font-bold text-base-50'>
							{items.length}
						</span>
					</div>

					<ul className='max-h-60 overflow-y-auto divide-y divide-base-200'>
						{items.map((item) => (
							<li
								key={item.id}
								className='group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-base-100'
							>
								<span className='mt-1 h-2 w-2 shrink-0 rounded-full bg-status-warning' />

								<div className='min-w-0 flex-1'>
									<p className='truncate text-sm font-medium text-base-950'>
										{item.section}
									</p>
									{item.description && item.description !== item.section && (
										<p className='mt-0.5 truncate text-xs text-base-600'>
											{item.description}
										</p>
									)}
								</div>

								<button
									type='button'
									onClick={() => handleRemove(item.id)}
									title='Descartar cambio'
									className='mt-0.5 shrink-0 rounded p-1 text-base-600 opacity-0 transition-all group-hover:opacity-100 hover:bg-status-error/10 hover:text-status-error'
								>
									<Trash size={14} />
								</button>
							</li>
						))}
					</ul>

					<div className='border-t border-base-300 px-4 py-3'>
						<button
							type='button'
							onClick={handleNavigateToPlan}
							className='btn btn-primary w-full'
						>
							<span>Revisar y aplicar</span>
							<ArrowRight color='' />
						</button>
					</div>
				</div>
			)}

			<button
				type='button'
				onClick={() => setOpen((v) => !v)}
				className='flex items-center gap-3 rounded-full border border-base-300 bg-base-50 py-2 pl-4 pr-3 shadow-[0_4px_12px_rgba(0,0,0,0.10)] transition-all hover:border-primary-100 hover:shadow-[0_4px_16px_rgba(83,168,62,0.20)]'
			>
				<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-100 px-1.5 text-xs font-bold text-base-50'>
					{items.length}
				</span>

				<span className='text-sm font-medium text-base-950'>
					{items.length === 1
						? '1 cambio en el plan'
						: `${items.length} cambios en el plan`}
				</span>

				<span className='text-base-600'>
					<ChevronIcon open={open} />
				</span>
			</button>
		</div>
	);
}
