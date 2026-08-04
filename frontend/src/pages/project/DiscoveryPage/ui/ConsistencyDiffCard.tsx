'use client';

import type { YourChange, DownstreamProposal } from '@/entities/consistency';
import { MarkdownText } from '@/shared/ui';

interface ConsistencyDiffCardProps {
	type: 'your_change' | 'downstream_impact';
	item: YourChange | DownstreamProposal;
	side: 'left' | 'right';
}

const getStatusOutline = (accepted: boolean | undefined) => {
	if (accepted === true) return 'outline-status-success';
	if (accepted === false) return 'outline-status-error';
	return 'outline-base-300';
};

export const ConsistencyDiffCard = ({
	type,
	item,
	side,
}: ConsistencyDiffCardProps) => {
	const accepted = item.accepted;
	const outlineClass = getStatusOutline(accepted);

	const displayId =
		type === 'downstream_impact'
			? (item as DownstreamProposal).targetDisplayId
			: '';

	const title =
		type === 'your_change'
			? (item as YourChange).section
			: (item as DownstreamProposal).targetTitle;

	const description =
		type === 'your_change'
			? (item as YourChange).description
			: (item as DownstreamProposal).rationale;

	const content = side === 'left' ? item.diff.before : item.diff.after;

	return (
		<div className={`m-0.5 px-8 py-4 inline-flex justify-start items-start gap-7 transition-shadow outline ${outlineClass}`}>
			{displayId && (
				<div className='w-14 inline-flex flex-col text-xl font-semibold justify-center my-auto items-center gap-2.5'>
					{displayId}
				</div>
			)}
			<div className='flex-1 inline-flex flex-col justify-center gap-2.5'>
				<h3 className='text-primary-100 text-xl font-semibold'>{title}</h3>
				<p className='text-base-800'>{description}</p>
				<div className='mt-2 max-h-60 overflow-y-auto rounded outline outline-base-300 px-5 py-3'>
					<MarkdownText content={content} className='text-sm text-base-800' />
				</div>
			</div>
		</div>
	);
};
