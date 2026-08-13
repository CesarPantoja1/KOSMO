'use client';

import type { YourChange, DownstreamProposal } from '@/entities/consistency';
import { PlantUmlViewer } from '@/feature';
import { MarkdownText } from '@/shared/ui';
import { useState } from 'react';

interface ConsistencyDiffCardProps {
	type: 'your_change' | 'downstream_impact';
	item: YourChange | DownstreamProposal;
	onAccept?: () => void;
	onReject?: () => void;
	onUndo?: () => void;
	accepting?: boolean;
}

const getStatusBorder = (accepted: boolean | undefined) => {
	if (accepted === true) return 'border-success-500';
	if (accepted === false) return 'border-error-500';
	return 'border-neutral-200';
};

const actionBadge = (action: string | undefined) => {
	if (action === 'delete') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-error-50 px-2 py-0.5 text-xs font-semibold text-error-700 border border-error-200'>
				Eliminar
			</span>
		);
	}
	if (action === 'update') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-warning-50 px-2 py-0.5 text-xs font-semibold text-warning-700 border border-warning-200'>
				Modificar
			</span>
		);
	}
	if (action === 'create' || action === 'new') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-success-50 px-2 py-0.5 text-xs font-semibold text-success-700 border border-success-200'>
				Nuevo
			</span>
		);
	}
	return null;
};

function DiffContent({
	field,
	before,
	after,
}: {
	field?: string;
	before: string;
	after: string;
}) {
	if (field === 'diagram_syntax' || field?.includes('plantuml')) {
		return (
			<div className='flex gap-4 mb-3'>
				<div className='flex-1 min-w-0'>
					<div className='text-xs font-semibold text-neutral-400 uppercase mb-1'>Actual</div>
					<div className='max-h-64 overflow-auto rounded border border-neutral-200 bg-neutral-50 p-2'>
						<PlantUmlViewer source={before} />
					</div>
				</div>
				<div className='flex-1 min-w-0'>
					<div className='text-xs font-semibold text-neutral-400 uppercase mb-1'>
						Propuesto
					</div>
					<div className='max-h-64 overflow-auto rounded border border-neutral-200 bg-neutral-50 p-2'>
						<PlantUmlViewer source={after} />
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className='flex gap-4 mb-3'>
			<div className='flex-1 min-w-0'>
				<div className='text-xs font-semibold text-neutral-400 uppercase mb-1'>Actual</div>
				<div className='max-h-48 overflow-y-auto rounded border border-neutral-200 px-4 py-2 bg-neutral-50'>
					<MarkdownText content={before || ''} className='text-sm text-neutral-800' />
				</div>
			</div>
			<div className='flex-1 min-w-0'>
				<div className='text-xs font-semibold text-neutral-400 uppercase mb-1'>
					Propuesto
				</div>
				<div className='max-h-48 overflow-y-auto rounded border border-neutral-200 px-4 py-2 bg-neutral-50'>
					<MarkdownText content={after || ''} className='text-sm text-neutral-800' />
				</div>
			</div>
		</div>
	);
}

export const ConsistencyDiffCard = ({
	type,
	item,
	onAccept,
	onReject,
	onUndo,
	accepting,
}: ConsistencyDiffCardProps) => {
	const accepted = item.accepted;
	const borderClass = getStatusBorder(accepted);
	const [showFullRationale, setShowFullRationale] = useState(false);

	const displayId =
		type === 'downstream_impact' ? (item as DownstreamProposal).targetDisplayId : '';

	const title =
		type === 'your_change'
			? (item as YourChange).section
			: (item as DownstreamProposal).targetTitle;

	const rationale =
		type === 'your_change'
			? (item as YourChange).description
			: (item as DownstreamProposal).rationale;

	const action =
		type === 'downstream_impact' ? (item as DownstreamProposal).action : undefined;

	const artifactType =
		type === 'downstream_impact' ? (item as DownstreamProposal).artifact_type : '';

	const diff = item.diff;
	const hasDiff = diff?.before || diff?.after;
	const diffField =
		(diff && 'field' in diff ? (diff as { field: string }).field : '') || '';
	const isDelete = action === 'delete';
	const isHandled = accepted !== undefined;
	const isFeatureDelete = artifactType === 'Feature' && isDelete;
	const isChildDelete = artifactType !== 'Feature' && isDelete;

	const hasActions = !isHandled && !isChildDelete;
	const hasUndo = isHandled;

	return (
		<div
			className={`bg-neutral-0 rounded-lg border ${borderClass} shadow-sm px-6 py-4 transition-shadow hover:shadow-md`}
		>
			<div className='flex items-start gap-4'>
				{displayId && (
					<div className='w-14 shrink-0 text-lg font-semibold text-neutral-700 pt-0.5 text-center'>
						{displayId}
					</div>
				)}
				<div className='flex-1 min-w-0'>
					<div className='flex items-center gap-2 mb-1'>
						<h3 className='text-neutral-800 text-base font-semibold truncate'>{title}</h3>
						{actionBadge(action)}
						{isHandled && (
							<span
								className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${accepted ? 'bg-success-50 text-success-700 border border-success-200' : 'bg-error-50 text-error-700 border border-error-200'}`}
							>
								{accepted ? 'Aceptado' : 'Descartado'}
							</span>
						)}
					</div>

					{rationale && (
						<div className='mb-3'>
							{showFullRationale || rationale.length <= 150 ? (
								<p className='text-sm text-neutral-600 leading-relaxed'>{rationale}</p>
							) : (
								<p className='text-sm text-neutral-600 leading-relaxed'>
									{rationale.slice(0, 150)}…
									<button
										type='button'
										onClick={() => setShowFullRationale(true)}
										className='ml-1 cursor-pointer text-neutral-800 underline text-xs'
									>
										Ver detalle
									</button>
								</p>
							)}
						</div>
					)}

					{isChildDelete && (
						<p className='text-sm text-neutral-500 italic mb-3'>
							Se eliminará en cascada al eliminar la característica asociada.
						</p>
					)}

					{hasDiff && (
						<DiffContent
							field={diffField}
							before={diff?.before || ''}
							after={diff?.after || ''}
						/>
					)}

					{!hasDiff && !isDelete && (
						<p className='text-sm text-neutral-500 italic mb-3'>
							Revisión manual requerida — el cambio no incluye diff automático. Consulta
							la justificación arriba.
						</p>
					)}

					<div className='flex items-center gap-2'>
						{hasActions && !isDelete && onAccept && (
							<button
								type='button'
								onClick={onAccept}
								disabled={accepting}
								className='btn btn-primary'
							>
								{accepting ? 'Aplicando...' : 'Aceptar'}
							</button>
						)}
						{isFeatureDelete && onAccept && (
							<button
								type='button'
								onClick={onAccept}
								disabled={accepting}
								className='btn btn-primary'
							>
								{accepting ? 'Aplicando...' : 'Aceptar eliminación'}
							</button>
						)}
						{hasActions && onReject && (
							<button type='button' onClick={onReject} className='btn btn-secondary'>
								Descartar
							</button>
						)}
						{hasUndo && onUndo && (
							<button type='button' onClick={onUndo} className='btn btn-warning'>
								Deshacer
							</button>
						)}
					</div>
				</div>
			</div>
		</div>
	);
};
