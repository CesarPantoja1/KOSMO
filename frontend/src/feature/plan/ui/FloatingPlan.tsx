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
				<div className='w-80 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-0 shadow-lg'>
					<div className='flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-4 py-3'>
						<span className='text-xs font-semibold uppercase tracking-wide text-neutral-500'>
							Cambios pendientes
						</span>
						<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-500 px-1.5 text-xs font-bold text-neutral-0'>
							{items.length}
						</span>
					</div>

					<ul className='max-h-60 overflow-y-auto divide-y divide-neutral-100'>
						{items.map((item) => (
							<li
								key={item.id}
								className='group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-neutral-50'
							>
								<span className='mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-warning-500' />

								<div className='min-w-0 flex-1'>
									<p className='truncate text-sm font-medium text-neutral-800'>
										{item.section}
									</p>
									{item.description && item.description !== item.section && (
										<p className='mt-0.5 truncate text-xs text-neutral-500'>
											{item.description}
										</p>
									)}
								</div>

								<button
									type='button'
									onClick={() => handleRemove(item.id)}
									title='Descartar sugerencia'
									className='mt-0.5 shrink-0 rounded-md p-1 text-neutral-400 opacity-0 transition-all group-hover:opacity-100 hover:bg-error-50 hover:text-error-500'
								>
									<Trash size={14} />
								</button>
							</li>
						))}
					</ul>

					<div className='border-t border-neutral-200 px-4 py-3'>
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

			{/* Toggle pill */}
			<button
				type='button'
				onClick={() => setOpen((v) => !v)}
				className='flex items-center gap-2.5 rounded-full border border-neutral-200 bg-neutral-0 py-2.5 pl-4 pr-3 shadow-md transition-all hover:border-primary-500 hover:shadow-[0_4px_16px_rgba(83,168,62,0.20)]'
			>
				<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-500 px-1.5 text-xs font-bold text-neutral-0'>
					{items.length}
				</span>
				<span className='text-sm font-medium text-neutral-800'>
					{items.length === 1
						? '1 cambio pendiente'
						: `${items.length} cambios pendientes`}
				</span>
				<span className='text-neutral-400'>
					<ChevronIcon open={open} />
				</span>
			</button>
		</div>
	);
}
