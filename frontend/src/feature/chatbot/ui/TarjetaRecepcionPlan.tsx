'use client';

import Check from '@/shared/ui/icons/Check';
import { MarkdownText } from '@/shared/ui/markdown-text';
import type { ChangeSuggestion } from '../types/chatbot';

interface Props {
	suggestion: ChangeSuggestion;
}

export const TarjetaRecepcionPlan = ({ suggestion }: Props) => {
	const isDeletion = suggestion.diff_after != null && !suggestion.diff_after.trim();

	return (
		<div className='mt-2 flex flex-col gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-4 shadow-sm'>
			<div className='flex items-start justify-between gap-2'>
				<h4 className='text-sm font-semibold text-neutral-800'>{suggestion.section}</h4>
				<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-500'>
					<Check size={12} /> Aplicado
				</span>
			</div>

			{suggestion.rationale && (
				<p className='text-xs italic text-neutral-500'>{suggestion.rationale}</p>
			)}

			<div className='flex flex-col gap-1.5 overflow-hidden rounded-md border border-neutral-200 text-xs'>
				{isDeletion && suggestion.diff_before && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Eliminar
						</div>
						<MarkdownText content={suggestion.diff_before} />
					</div>
				)}
				{suggestion.diff_before && !isDeletion && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Anterior
						</div>
						<MarkdownText content={suggestion.diff_before} />
					</div>
				)}
				{!isDeletion && suggestion.diff_after && (
					<div className='border-l-2 border-primary-500 bg-primary-50 p-2.5 text-primary-900 [&_pre]:!bg-primary-100 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						{suggestion.diff_before && (
							<div className='mb-1 font-mono text-[10px] font-semibold text-primary-500 uppercase tracking-wider'>
								+ Propuesto
							</div>
						)}
						<MarkdownText content={suggestion.diff_after} />
					</div>
				)}
			</div>
		</div>
	);
};
