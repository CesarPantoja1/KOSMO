'use client';

import { usePlanStore } from '@/entities/plan';
import { normalizeDiff } from '@/entities/plan/model/normalizeDiff';
import Check from '@/shared/ui/icons/Check';
import Close from '@/shared/ui/icons/Close';
import Plus from '@/shared/ui/icons/Plus';
import Trash from '@/shared/ui/icons/Trash';
import { MarkdownText } from '@/shared/ui/markdown-text';
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
	} else if (
		ACTIVE_STATUSES.includes(planChange.status as (typeof ACTIVE_STATUSES)[number])
	) {
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

	const isDeletion = suggestion.diff_after != null && !suggestion.diff_after.trim();

	const { before: normalizedBefore, after: normalizedAfter } = normalizeDiff(
		suggestion.diff_before || '',
		suggestion.diff_after || '',
	);
	const wasNormalized = normalizedBefore === '' && suggestion.diff_before !== '';

	const isPureAddition =
		isNoSpec ||
		(!isDeletion && suggestion.diff_before?.trim() === suggestion.diff_after?.trim()) ||
		wasNormalized;
	const isModification = !isPureAddition && !isDeletion;
	const hasDiffBefore = Boolean(normalizedBefore && isModification);
	const displayAfter = wasNormalized ? normalizedAfter : suggestion.diff_after;

	return (
		<div className='mt-2 flex flex-col gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-4 shadow-sm'>
			{/* Header: sección + badge de estado */}
			<div className='flex items-start justify-between gap-2'>
				<div className='flex items-center gap-2 flex-wrap'>
					<h4 className='text-sm font-semibold text-neutral-800'>{suggestion.section}</h4>
					{isPureAddition && (
						<span className='rounded-full bg-success-50 px-2 py-0.5 text-[10px] font-medium text-success-700'>
							Nuevo
						</span>
					)}
					{isModification && (
						<span className='rounded-full bg-warning-50 px-2 py-0.5 text-[10px] font-medium text-warning-700'>
							Modificar
						</span>
					)}
					{isDeletion && (
						<span className='rounded-full bg-error-50 px-2 py-0.5 text-[10px] font-medium text-error-700'>
							Eliminar
						</span>
					)}
				</div>
				{status === 'added' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-500'>
						<Check size={12} /> Agregado
					</span>
				)}
				{status === 'applied' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-500'>
						<Check size={12} /> Aplicado
					</span>
				)}
				{status === 'discarded' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500'>
						<Close size={12} color='text-neutral-500' /> Descartado
					</span>
				)}
			</div>

			{/* Rationale */}
			{suggestion.rationale && (
				<p className='text-xs italic text-neutral-500'>{suggestion.rationale}</p>
			)}

			{/* Diff */}
			<div className='flex flex-col gap-1.5 overflow-hidden rounded-md border border-neutral-200 text-xs'>
				{isDeletion && suggestion.diff_before && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Eliminar
						</div>
						<MarkdownText content={suggestion.diff_before} />
					</div>
				)}
				{hasDiffBefore && (
					<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
							- Anterior
						</div>
						<MarkdownText content={suggestion.diff_before} />
					</div>
				)}
				{!isDeletion && displayAfter && (
					<div className='border-l-2 border-primary-500 bg-primary-50 p-2.5 text-primary-900 [&_pre]:!bg-primary-100 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
						{isModification && (
							<div className='mb-1 font-mono text-[10px] font-semibold text-primary-500 uppercase tracking-wider'>
								+ Propuesto
							</div>
						)}
						<MarkdownText content={displayAfter} />
					</div>
				)}
			</div>

			{/* Acciones */}
			{status !== 'applied' && (
				<div className='flex justify-end gap-2'>
					{status === 'pending' && (
						<>
							<button className='btn-chat btn-destructive' onClick={handleDiscard}>
								<Trash size={13} />
								Descartar
							</button>
							<button className='btn-chat btn-primary' onClick={handleAdd}>
								<Plus size={13} color='' />
								Agregar al plan
							</button>
						</>
					)}
					{status === 'added' && (
						<button className='btn-chat btn-destructive' onClick={handleRemove}>
							<Trash size={13} />
							Quitar del plan
						</button>
					)}
					{status === 'discarded' && (
						<button className='btn-chat btn-primary' onClick={handleAdd}>
							<Plus size={13} color='' />
							Agregar al plan
						</button>
					)}
				</div>
			)}
		</div>
	);
};
