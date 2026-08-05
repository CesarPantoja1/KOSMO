'use client';

import { useCallback, useMemo, useRef } from 'react';

import { ArrowLeft } from '@/shared/ui';
import { computeWordDiff } from '../lib/computeWordDiff';
import { WordDiffView } from './word-diff-view';

interface Props {
	original: string;
	proposal: string;
	onBack: () => void;
	onDiscard: () => void;
	onApply: () => void;
	originalLabel?: string;
	proposalLabel?: string;
	processing?: boolean;
}

export function MarkdownDiff({
	original,
	proposal,
	onBack,
	onDiscard,
	onApply,
	originalLabel = 'Original',
	proposalLabel = 'Propuesta',
	processing = false,
}: Props) {
	const leftRef = useRef<HTMLDivElement>(null);
	const rightRef = useRef<HTMLDivElement>(null);
	const isSyncingLeft = useRef(false);
	const isSyncingRight = useRef(false);

	const chunks = useMemo(() => computeWordDiff(original, proposal), [original, proposal]);

	const handleLeftScroll = useCallback(() => {
		if (isSyncingRight.current) return;
		const left = leftRef.current;
		const right = rightRef.current;
		if (!left || !right) return;
		isSyncingLeft.current = true;
		const ratio = left.scrollTop / (left.scrollHeight - left.clientHeight || 1);
		right.scrollTop = ratio * (right.scrollHeight - right.clientHeight);
		isSyncingLeft.current = false;
	}, []);

	const handleRightScroll = useCallback(() => {
		if (isSyncingLeft.current) return;
		const left = leftRef.current;
		const right = rightRef.current;
		if (!left || !right) return;
		isSyncingRight.current = true;
		const ratio = right.scrollTop / (right.scrollHeight - right.clientHeight || 1);
		left.scrollTop = ratio * (left.scrollHeight - left.clientHeight);
		isSyncingRight.current = false;
	}, []);

	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden bg-base-50'>
			{/* Header */}
			<div className='flex shrink-0 items-center justify-between border-b border-base-300 bg-base-100 px-6 py-3'>
				<div className='flex flex-1 items-center gap-2'>
					<span className='flex-1 text-center text-sm font-semibold text-base-950'>
						{originalLabel}
					</span>
					<div className='w-px self-stretch bg-base-300' />
					<span className='flex-1 text-center text-sm font-semibold text-base-950'>
						{proposalLabel}
					</span>
				</div>
				<button
					type='button'
					onClick={onBack}
					className='btn text-base-50 bg-primary-100 hover:bg-primary-100/90 rounded-sm mt-2'
				>
					<ArrowLeft color='' size={20} />
					Volver
				</button>
			</div>

			{/* Panels */}
			<div className='flex min-h-0 flex-1 overflow-hidden'>
				{/* Left — Original */}
				<div ref={leftRef} onScroll={handleLeftScroll} className='flex-1 overflow-y-auto'>
					<WordDiffView chunks={chunks} side='left' />
				</div>

				{/* Divider */}
				<div className='w-px shrink-0 bg-base-300' />

				{/* Right — Proposal */}
				<div
					ref={rightRef}
					onScroll={handleRightScroll}
					className='flex-1 overflow-y-auto'
				>
					<WordDiffView chunks={chunks} side='right' />
				</div>
			</div>

			{/* Footer */}
			<div className='flex shrink-0 items-center justify-between border-t border-base-300 bg-base-100 px-6 py-4'>
				<button
					type='button'
					onClick={onDiscard}
					className='cursor-pointer rounded-md border border-status-error bg-white px-5 py-2 text-sm font-medium text-status-error transition-colors hover:bg-status-error hover:text-white active:opacity-80'
				>
					Descartar Cambios
				</button>
				<button
					type='button'
					onClick={onApply}
					disabled={processing}
					className={`rounded-md px-5 py-2 text-sm font-medium text-white transition-colors ${
						processing
							? 'cursor-not-allowed bg-primary-100/50'
							: 'cursor-pointer bg-primary-100 hover:bg-primary-800 active:opacity-80'
					}`}
				>
					{processing ? 'Aplicando...' : 'Aplicar Cambios'}
				</button>
			</div>
		</div>
	);
}
