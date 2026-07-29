import { useState } from 'react';
import type { ChangeSuggestion } from '../types/chatbot';
import { ButtonSM } from '@/shared/ui/button';
import Check from '@/shared/ui/icons/Check';
import Trash from '@/shared/ui/icons/Trash';
import Plus from '@/shared/ui/icons/Plus';
import Close from '@/shared/ui/icons/Close';

interface TarjetaRecepcionPlanProps {
	suggestion: ChangeSuggestion;
	onAction?: (action: 'add' | 'remove' | 'discard') => void;
}

export type PlanChangeStatus = 'pending' | 'added' | 'discarded';

export const TarjetaRecepcionPlan = ({ suggestion, onAction }: TarjetaRecepcionPlanProps) => {
	const [status, setStatus] = useState<PlanChangeStatus>('pending');

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
		<div className="mt-4 border rounded-md p-4 bg-white shadow-sm flex flex-col gap-3">
			<div className="flex justify-between items-start">
				<h4 className="font-semibold text-sm text-text">Sugerencia: {suggestion.section}</h4>
				{status === 'added' && (
					<span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full font-medium">
						<Check size={14} /> Agregado
					</span>
				)}
				{status === 'discarded' && (
					<span className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full font-medium">
						<Close size={14} color="text-gray-500" /> Descartado
					</span>
				)}
			</div>
			
			{suggestion.rationale && (
				<p className="text-xs text-gray-600 italic">{suggestion.rationale}</p>
			)}

			<div className="flex flex-col gap-2 font-mono text-xs overflow-hidden rounded border bg-gray-50">
				{suggestion.diff_before && (
					<div className="p-2 bg-red-50 text-red-800 border-l-2 border-red-500 line-through decoration-red-400">
						{suggestion.diff_before}
					</div>
				)}
				{suggestion.diff_after && (
					<div className="p-2 bg-green-50 text-green-800 border-l-2 border-green-500">
						{suggestion.diff_after}
					</div>
				)}
			</div>

			<div className="flex justify-end gap-2 mt-1">
				{status === 'pending' && (
					<>
						<ButtonSM variant="secondary" onClick={handleDiscard} icon={<Trash size={14} />}>
							Descartar
						</ButtonSM>
						<ButtonSM variant="primary" onClick={handleAdd} icon={<Plus size={14} color="text-white" />}>
							Agregar al plan
						</ButtonSM>
					</>
				)}
				{status === 'added' && (
					<ButtonSM variant="destructive" onClick={handleRemove} icon={<Trash size={14} color="text-white" />}>
						Quitar del plan
					</ButtonSM>
				)}
			</div>
		</div>
	);
};
