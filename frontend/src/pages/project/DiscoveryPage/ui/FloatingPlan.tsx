'use client';

import { deletePlanChange, usePlanStore } from '@/entities/plan';
import { toast } from '@/shared/ui';
import Trash from '@/shared/ui/icons/Trash';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

function ChevronIcon({ open }: { open: boolean }) {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={14}
			height={14}
			className={`fill-current transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
		>
			<path
				fillRule='evenodd'
				clipRule='evenodd'
				d='M12.53 16.28a.75.75 0 0 1-1.06 0l-7.5-7.5a.75.75 0 0 1 1.06-1.06L12 14.69l6.97-6.97a.75.75 0 1 1 1.06 1.06l-7.5 7.5Z'
			/>
		</svg>
	);
}

function ArrowRightIcon() {
	return (
		<svg
			xmlns='http://www.w3.org/2000/svg'
			viewBox='0 0 24 24'
			width={14}
			height={14}
			className='fill-current'
		>
			<path
				fillRule='evenodd'
				clipRule='evenodd'
				d='M12.97 3.97a.75.75 0 0 1 1.06 0l7.5 7.5a.75.75 0 0 1 0 1.06l-7.5 7.5a.75.75 0 1 1-1.06-1.06l6.22-6.22H3a.75.75 0 0 1 0-1.5h16.19l-6.22-6.22a.75.75 0 0 1 0-1.06Z'
			/>
		</svg>
	);
}

export function FloatingDiscoveryPlan() {
	const [open, setOpen] = useState(false);
	const router = useRouter();

	const currentProject = useAppStore((s) => s.currentProject);
	const planByPhase = usePlanStore((s) => s.planByPhase);
	const removeFromPlan = usePlanStore((s) => s.removeFromPlan);

	const items = planByPhase['discovery'] ?? [];

	if (items.length === 0) return null;

	const handleRemove = async (changeId: string) => {
		if (!currentProject) return;
		removeFromPlan('discovery', changeId);
		try {
			await deletePlanChange(currentProject.id, 'discovery', changeId);
		} catch (err) {
			console.warn('[FloatingDiscoveryPlan] Error al eliminar cambio:', err);
			toast.error('No se pudo eliminar el cambio del plan');
		}
	};

	const handleNavigateToPlan = () => {
		router.push('/proyecto/descubrimiento/plan');
	};

	return (
		<div className='absolute bottom-6 right-2 z-50 flex flex-col items-end gap-2'>
			{/* Panel de items — se muestra al expandir */}
			{open && (
				<div className='w-80 overflow-hidden rounded-xl border border-base-300 bg-base-50 shadow-[0_8px_24px_rgba(0,0,0,0.12)]'>
					{/* Header del panel */}
					<div className='flex items-center justify-between border-b border-base-300 bg-base-100 px-4 py-3'>
						<span className='text-xs font-semibold uppercase tracking-wide text-base-600'>
							Cambios pendientes
						</span>
						<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-100 px-1.5 text-xs font-bold text-base-50'>
							{items.length}
						</span>
					</div>

					{/* Lista de cambios */}
					<ul className='max-h-60 overflow-y-auto divide-y divide-base-200'>
						{items.map((item) => (
							<li
								key={item.id}
								className='group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-base-100'
							>
								{/* Indicador de estado */}
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

								{/* Botón eliminar */}
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

					{/* Footer — acceso rápido a la página del plan */}
					<div className='border-t border-base-300 px-4 py-3'>
						<button
							type='button'
							onClick={handleNavigateToPlan}
							className='btn w-full justify-center bg-primary-100 text-sm text-base-50 hover:bg-primary-800'
						>
							<span>Revisar y aplicar</span>
							<ArrowRightIcon />
						</button>
					</div>
				</div>
			)}

			{/* Pill flotante */}
			<button
				type='button'
				onClick={() => setOpen((v) => !v)}
				className='flex items-center gap-3 rounded-full border border-base-300 bg-base-50 py-2 pl-4 pr-3 shadow-[0_4px_12px_rgba(0,0,0,0.10)] transition-all hover:border-primary-100 hover:shadow-[0_4px_16px_rgba(83,168,62,0.20)]'
			>
				{/* Badge contador */}
				<span className='flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-100 px-1.5 text-xs font-bold text-base-50'>
					{items.length}
				</span>

				{/* Texto */}
				<span className='text-sm font-medium text-base-950'>
					{items.length === 1
						? '1 cambio en el plan'
						: `${items.length} cambios en el plan`}
				</span>

				{/* Chevron */}
				<span className='text-base-600'>
					<ChevronIcon open={open} />
				</span>
			</button>
		</div>
	);
}
