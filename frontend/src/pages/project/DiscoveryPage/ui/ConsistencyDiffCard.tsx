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
	onDelete?: () => void;
	accepting?: boolean;
}

const getStatusOutline = (accepted: boolean | undefined) => {
	if (accepted === true) return 'outline-status-success';
	if (accepted === false) return 'outline-status-error';
	return 'outline-base-300';
};

const actionBadge = (action: string | undefined) => {
	if (action === 'delete') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700'>
				Eliminar
			</span>
		);
	}
	if (action === 'update') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700'>
				Modificar
			</span>
		);
	}
	if (action === 'create' || action === 'new') {
		return (
			<span className='ml-2 shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700'>
				Nuevo
			</span>
		);
	}
	return null;
};

function DiffContent({ field, before, after }: { field?: string; before: string; after: string }) {
	if (field === 'diagram_syntax' || field?.includes('plantuml')) {
		return (
			<div className='flex gap-4 mb-3'>
				<div className='flex-1 min-w-0'>
					<div className='text-xs font-semibold text-base-400 uppercase mb-1'>Actual</div>
					<div className='max-h-64 overflow-auto rounded outline outline-base-300 bg-base-50 p-2'>
						<PlantUmlViewer source={before} />
					</div>
				</div>
				<div className='flex-1 min-w-0'>
					<div className='text-xs font-semibold text-base-400 uppercase mb-1'>Propuesto</div>
					<div className='max-h-64 overflow-auto rounded outline outline-base-300 bg-base-50 p-2'>
						<PlantUmlViewer source={after} />
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className='flex gap-4 mb-3'>
			<div className='flex-1 min-w-0'>
				<div className='text-xs font-semibold text-base-400 uppercase mb-1'>Actual</div>
				<div className='max-h-48 overflow-y-auto rounded outline outline-base-300 px-4 py-2 bg-base-50'>
					<MarkdownText content={before || ''} className='text-sm text-base-800' />
				</div>
			</div>
			<div className='flex-1 min-w-0'>
				<div className='text-xs font-semibold text-base-400 uppercase mb-1'>Propuesto</div>
				<div className='max-h-48 overflow-y-auto rounded outline outline-base-300 px-4 py-2 bg-base-50'>
					<MarkdownText content={after || ''} className='text-sm text-base-800' />
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
	onDelete,
	accepting,
}: ConsistencyDiffCardProps) => {
	const accepted = item.accepted;
	const outlineClass = getStatusOutline(accepted);
	const [showFullRationale, setShowFullRationale] = useState(false);

	const displayId =
		type === 'downstream_impact'
			? (item as DownstreamProposal).targetDisplayId
			: '';

	const title =
		type === 'your_change'
			? (item as YourChange).section
			: (item as DownstreamProposal).targetTitle;

	const rationale =
		type === 'your_change'
			? (item as YourChange).description
			: (item as DownstreamProposal).rationale;

	const action =
		type === 'downstream_impact'
			? (item as DownstreamProposal).action
			: undefined;

	const artifactType =
		type === 'downstream_impact'
			? (item as DownstreamProposal).artifact_type
			: '';

	const diff = item.diff;
	const hasDiff = diff?.before || diff?.after;
	const diffField = (diff && 'field' in diff ? (diff as { field: string }).field : '') || '';
	const isDelete = action === 'delete';
	const isHandled = accepted !== undefined;
	const isFeatureDelete = artifactType === 'Feature' && isDelete;
	const isChildDelete = artifactType !== 'Feature' && isDelete;

	const hasActions = !isHandled && !isChildDelete;
	const hasUndo = isHandled;

	return (
		<div className={`mx-0.5 mb-2 px-6 py-4 transition-shadow outline rounded ${outlineClass}`}>
			<div className='flex items-start gap-4'>
				{displayId && (
					<div className='w-14 shrink-0 text-lg font-semibold text-base-800 pt-0.5 text-center'>
						{displayId}
					</div>
				)}
				<div className='flex-1 min-w-0'>
					<div className='flex items-center gap-2 mb-1'>
						<h3 className='text-primary-100 text-lg font-semibold truncate'>{title}</h3>
						{actionBadge(action)}
						{isHandled && (
							<span className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${accepted ? 'bg-status-success/10 text-status-success' : 'bg-status-error/10 text-status-error'}`}>
								{accepted ? 'Aceptado' : 'Descartado'}
							</span>
						)}
					</div>

					{rationale && (
						<div className='mb-3'>
							{showFullRationale || rationale.length <= 150 ? (
								<p className='text-sm text-base-600 leading-relaxed'>{rationale}</p>
							) : (
								<p className='text-sm text-base-600 leading-relaxed'>
									{rationale.slice(0, 150)}…
									<button
										type='button'
										onClick={() => setShowFullRationale(true)}
										className='ml-1 cursor-pointer text-primary-90 underline text-xs'
									>
										Ver detalle
									</button>
								</p>
							)}
						</div>
					)}

					{isChildDelete && (
						<p className='text-sm text-base-500 italic mb-3'>
							Se eliminará en cascada al eliminar la característica asociada.
						</p>
					)}

					{hasDiff && (
						<DiffContent field={diffField} before={diff?.before || ''} after={diff?.after || ''} />
					)}

					{!hasDiff && !isDelete && (
						<p className='text-sm text-base-500 italic mb-3'>
							Revisión manual requerida — el cambio no incluye diff automático. Consulta la justificación arriba.
						</p>
					)}

					<div className='flex items-center gap-2'>
						{hasActions && !isDelete && onAccept && (
							<button
								type='button'
								onClick={onAccept}
								disabled={accepting}
								className='cursor-pointer rounded-md bg-status-success px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-status-success/90 active:opacity-80 disabled:opacity-50'
							>
								{accepting ? 'Aplicando...' : 'Aceptar'}
							</button>
						)}
						{isFeatureDelete && onAccept && (
							<button
								type='button'
								onClick={onAccept}
								disabled={accepting}
								className='cursor-pointer rounded-md bg-status-success px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-status-success/90 active:opacity-80 disabled:opacity-50'
							>
								{accepting ? 'Aplicando...' : 'Aceptar eliminación'}
							</button>
						)}
						{hasActions && onReject && (
							<button
								type='button'
								onClick={onReject}
								className='cursor-pointer rounded-md border border-base-300 bg-white px-4 py-1.5 text-sm font-medium text-base-600 transition-colors hover:bg-base-100 active:bg-base-200'
							>
								Descartar
							</button>
						)}
						{hasUndo && onUndo && (
							<button
								type='button'
								onClick={onUndo}
								className='cursor-pointer rounded-md border border-amber-300 bg-white px-4 py-1.5 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-50 active:bg-amber-100'
							>
								Deshacer
							</button>
						)}
					</div>
				</div>
			</div>
		</div>
	);
};
