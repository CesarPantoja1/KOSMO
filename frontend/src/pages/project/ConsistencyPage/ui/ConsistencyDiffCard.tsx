'use client';

import type { YourChange, DownstreamProposal } from '@/entities/consistency';

interface ConsistencyDiffCardProps {
	type: 'your_change' | 'downstream_impact';
	item: YourChange | DownstreamProposal;
	onAccept?: () => void;
	onReject?: () => void;
}

const getStatusBorder = (accepted: boolean | undefined) => {
	if (accepted === true) return 'border-l-status-success';
	if (accepted === false) return 'border-l-status-error';
	return 'border-l-base-300';
};

const getStatusBadge = (accepted: boolean | undefined) => {
	if (accepted === true)
		return <span className='text-xs font-medium text-status-success'>Aceptado</span>;
	if (accepted === false)
		return <span className='text-xs font-medium text-status-error'>Rechazado</span>;
	return <span className='text-xs font-medium text-base-600'>Pendiente</span>;
};

export const ConsistencyDiffCard = ({
	type,
	item,
	onAccept,
	onReject,
}: ConsistencyDiffCardProps) => {
	const accepted = item.accepted;
	const borderClass = getStatusBorder(accepted);

	const title =
		type === 'your_change'
			? (item as YourChange).section
			: `${(item as DownstreamProposal).targetDisplayId} — ${(item as DownstreamProposal).targetTitle}`;

	const description =
		type === 'your_change'
			? (item as YourChange).description
			: (item as DownstreamProposal).rationale;

	const diff = item.diff;

	return (
		<div
			className={`rounded-lg border border-base-200 bg-white shadow-sm border-l-4 ${borderClass}`}
		>
			<div className='px-5 py-4'>
				<div className='mb-2 flex items-start justify-between'>
					<div className='flex-1'>
						<h3 className='text-sm font-semibold text-base-800'>{title}</h3>
						<p className='mt-0.5 text-xs text-base-600'>{description}</p>
					</div>
					<div className='ml-3 flex items-center gap-2'>{getStatusBadge(accepted)}</div>
				</div>

				<div className='mt-3 grid grid-cols-2 gap-3'>
					<div className='rounded-md bg-status-error/5 p-3'>
						<p className='mb-1 text-[10px] font-medium uppercase tracking-wider text-status-error'>
							Antes
						</p>
						<p className='whitespace-pre-wrap text-xs leading-relaxed text-base-800'>
							{diff.before}
						</p>
					</div>
					<div className='rounded-md bg-status-success/5 p-3'>
						<p className='mb-1 text-[10px] font-medium uppercase tracking-wider text-status-success'>
							Después
						</p>
						<p className='whitespace-pre-wrap text-xs leading-relaxed text-base-800'>
							{diff.after}
						</p>
					</div>
				</div>
			</div>

			{type === 'downstream_impact' && (
				<div className='flex items-center gap-2 border-t border-base-200 px-5 py-3'>
					<button
						type='button'
						onClick={onReject}
						className='cursor-pointer rounded-md border border-status-error bg-white px-4 py-1.5 text-xs font-medium text-status-error transition-colors hover:bg-status-error hover:text-white active:opacity-80'
					>
						Rechazar
					</button>
					<button
						type='button'
						onClick={onAccept}
						className='cursor-pointer rounded-md bg-status-success px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-status-success/90 active:opacity-80'
					>
						Aceptar
					</button>
				</div>
			)}
		</div>
	);
};
