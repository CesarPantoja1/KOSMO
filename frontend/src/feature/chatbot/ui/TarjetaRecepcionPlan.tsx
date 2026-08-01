'use client';

import { ButtonSM } from '@/shared/ui/button';
import Check from '@/shared/ui/icons/Check';
import Close from '@/shared/ui/icons/Close';
import Plus from '@/shared/ui/icons/Plus';
import Trash from '@/shared/ui/icons/Trash';
import { MarkdownText } from '@/shared/ui/markdown-text';
import { usePlanStore } from '@/entities/plan';
import { useState } from 'react';
import type { ChangeSuggestion } from '../types/chatbot';

interface Props {
	suggestion: ChangeSuggestion;
	messageId: string;
	onAction?: (action: 'add' | 'remove' | 'discard') => void;
}

type CardStatus = 'pending' | 'added' | 'applied' | 'discarded';

const ACTIVE_STATUSES = ['pending', 'added', 'conflict'] as const;

export const TarjetaRecepcionPlan = ({ suggestion, messageId, onAction }: Props) => {
	const [discarded, setDiscarded] = useState(false);

	const planByPhase = usePlanStore((s) => s.planByPhase);
	const planChange = Object.values(planByPhase)
		.flat()
		.find((c) => c.id === suggestion.id);

	let status: CardStatus;

	if (discarded) {
		status = 'discarded';
	} else if (planChange == null) {
		status = 'pending';
	} else if (planChange.status === 'applied') {
		status = 'applied';
	} else if (ACTIVE_STATUSES.includes(planChange.status as (typeof ACTIVE_STATUSES)[number])) {
		status = 'added';
	} else {
		status = 'discarded';
	}

	const handleAdd = () => {
		onAction?.('add');
	};
	const handleRemove = () => {
		onAction?.('remove');
	};
	const handleDiscard = () => {
		setDiscarded(true);
		onAction?.('discard');
	};

	const isNoSpec =
		!suggestion.diff_before ||
		suggestion.diff_before.trim().toLowerCase() === 'no especificado' ||
		suggestion.diff_before.trim().toLowerCase() === 'ninguno';

	const hasDiffBefore = Boolean(suggestion.diff_before && !isNoSpec);

	return (
		<div className='mt-2 flex flex-col gap-3 rounded-lg border border-base-300 bg-white p-4 shadow-sm'>
			{/* Header: sección + badge de estado */}
			<div className='flex items-start justify-between gap-2'>
				<div className='flex items-center gap-2 flex-wrap'>
					<h4 className='text-sm font-semibold text-base-950'>{suggestion.section}</h4>
					{isNoSpec && (
						<span className='rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800'>
							Nuevo
						</span>
					)}
				</div>
				{status === 'added' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-100'>
						<Check size={12} /> Agregado
					</span>
				)}
				{status === 'applied' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-100'>
						<Check size={12} /> Aplicado
					</span>
				)}
				{status === 'discarded' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-base-200 px-2 py-0.5 text-xs font-medium text-base-600'>
						<Close size={12} color='text-base-600' /> Descartado
					</span>
				)}
			</div>

			{/* Rationale */}
			{suggestion.rationale && (
				<p className='text-xs italic text-base-600'>{suggestion.rationale}</p>
			)}

			{/* Diff */}
			<div className='flex flex-col gap-1.5 overflow-hidden rounded-md border border-base-300 text-xs'>
				{hasDiffBefore && (
					<div className='border-l-2 border-status-error bg-status-error/5 p-2.5 text-status-error [&_pre]:!bg-status-error/10 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-status-error/80 uppercase tracking-wider'>
							- Anterior
						</div>
						<MarkdownText content={suggestion.diff_before} />
					</div>
				)}
				{suggestion.diff_after && (
					<div className='border-l-2 border-primary-100 bg-primary-50 p-2.5 text-primary-900 [&_pre]:!bg-primary-100/15 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						{hasDiffBefore && (
							<div className='mb-1 font-mono text-[10px] font-semibold text-primary-600 uppercase tracking-wider'>
								+ Propuesto
							</div>
						)}
						<MarkdownText content={suggestion.diff_after} />
					</div>
				)}
			</div>

			{/* Acciones */}
			{status !== 'applied' && (
				<div className='flex justify-end gap-2'>
					{status === 'pending' && (
						<>
							<ButtonSM
								variant='secondary'
								onClick={handleDiscard}
								icon={<Trash size={13} />}
							>
								Descartar
							</ButtonSM>
							<ButtonSM
								variant='primary'
								onClick={handleAdd}
								icon={<Plus size={13} color='text-white' />}
							>
								Agregar al plan
							</ButtonSM>
						</>
					)}
					{status === 'added' && (
						<ButtonSM
							variant='destructive'
							onClick={handleRemove}
							icon={<Trash size={13} color='text-white' />}
						>
							Quitar del plan
						</ButtonSM>
					)}
					{status === 'discarded' && (
						<ButtonSM
							variant='primary'
							onClick={handleAdd}
							icon={<Plus size={13} color='text-white' />}
						>
							Agregar al plan
						</ButtonSM>
					)}
				</div>
			)}
		</div>
	);
};
