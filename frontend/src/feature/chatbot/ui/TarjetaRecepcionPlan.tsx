'use client';

import { Change } from '@/entities/chat';
import Check from '@/shared/ui/icons/Check';
import { MarkdownText } from '@/shared/ui/markdown-text';

interface Props {
	change: Change;
}

export const TarjetaRecepcionPlan = ({ change }: Props) => {
	const isDeletion = change.after != null && !change.after.trim();

	return (
		<div className='mt-2 flex flex-col gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-4 shadow-sm'>
			<div className='flex items-start justify-between gap-2'>
				<h4 className='text-sm font-semibold text-neutral-800'>
					{change.change_description}
				</h4>

				{change.applied && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-500'>
						<Check size={12} /> Aplicado
					</span>
				)}
			</div>

			<div className='flex flex-col gap-1.5 overflow-hidden rounded-md border border-neutral-200 text-xs'>
				{isDeletion && change.before && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Eliminar
						</div>
						<MarkdownText content={change.before} />
					</div>
				)}
				{change.before && !isDeletion && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Anterior
						</div>
						<MarkdownText content={change.before} />
					</div>
				)}
				{!isDeletion && change.after && (
					<div className='border-l-2 border-primary-500 bg-primary-50 p-2.5 text-primary-900 [&_pre]:!bg-primary-100 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						{change.before && (
							<div className='mb-1 font-mono text-[10px] font-semibold text-primary-500 uppercase tracking-wider'>
								+ Propuesto
							</div>
						)}
						<MarkdownText content={change.after} />
					</div>
				)}
			</div>
		</div>
	);
};
