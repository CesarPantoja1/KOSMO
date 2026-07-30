'use client';

import { ButtonSM } from '@/shared/ui/button';
import Check from '@/shared/ui/icons/Check';
import Close from '@/shared/ui/icons/Close';
import Plus from '@/shared/ui/icons/Plus';
import Trash from '@/shared/ui/icons/Trash';
import { useState } from 'react';
import type { ChangeSuggestion } from '../types/chatbot';

interface Props {
	suggestion: ChangeSuggestion;
	onAction?: (action: 'add' | 'remove' | 'discard') => void;
}

type CardStatus = 'pending' | 'added' | 'discarded';

export const TarjetaRecepcionPlan = ({ suggestion, onAction }: Props) => {
	const [status, setStatus] = useState<CardStatus>('pending');

	const handleAdd = () => {
		setStatus('added');
		onAction?.('add');
	};
	const handleRemove = () => {
		setStatus('pending');
		onAction?.('remove');
	};
	const handleDiscard = () => {
		setStatus('discarded');
		onAction?.('discard');
	};

	return (
		<div className='mt-2 flex flex-col gap-3 rounded-lg border border-base-300 bg-white p-4 shadow-sm'>
			{/* Header: sección + badge de estado */}
			<div className='flex items-start justify-between gap-2'>
				<h4 className='text-sm font-semibold text-base-950'>{suggestion.section}</h4>
				{status === 'added' && (
					<span className='flex shrink-0 items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-100'>
						<Check size={12} /> Agregado
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
			<div className='flex flex-col gap-1 overflow-hidden rounded-md border border-base-300 font-mono text-xs'>
				{suggestion.diff_before && (
					<div className='border-l-2 border-status-error bg-status-error/5 p-2 text-status-error line-through decoration-status-error/50'>
						{suggestion.diff_before}
					</div>
				)}
				{suggestion.diff_after && (
					<div className='border-l-2 border-primary-100 bg-primary-50 p-2 text-primary-800'>
						{suggestion.diff_after}
					</div>
				)}
			</div>

			{/* Acciones */}
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
			</div>
		</div>
	);
};
