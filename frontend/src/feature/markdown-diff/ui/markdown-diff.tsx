'use client';

import { useCallback, useRef } from 'react';

import {
	headingsPlugin,
	listsPlugin,
	markdownShortcutPlugin,
	MDXEditor,
	quotePlugin,
	thematicBreakPlugin,
} from '@mdxeditor/editor';

import '@mdxeditor/editor/style.css';

interface Props {
	original: string;
	proposal: string;
	onBack: () => void;
	onDiscard: () => void;
	onApply: () => void;
	originalLabel?: string;
	proposalLabel?: string;
}

const PLUGINS = [
	headingsPlugin(),
	listsPlugin(),
	quotePlugin(),
	thematicBreakPlugin(),
	markdownShortcutPlugin(),
];

export function MarkdownDiff({
	original,
	proposal,
	onBack,
	onDiscard,
	onApply,
	originalLabel = 'Original',
	proposalLabel = 'Propuesta',
}: Props) {
	const leftRef = useRef<HTMLDivElement>(null);
	const rightRef = useRef<HTMLDivElement>(null);
	const isSyncingLeft = useRef(false);
	const isSyncingRight = useRef(false);

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
					className='ml-6 cursor-pointer rounded-md border border-base-300 bg-white px-4 py-1.5 text-sm font-medium text-base-950 transition-colors hover:bg-base-100 active:bg-base-200'
				>
					Volver
				</button>
			</div>

			{/* Panels */}
			<div className='flex min-h-0 flex-1 overflow-hidden'>
				{/* Left — Original */}
				<div ref={leftRef} onScroll={handleLeftScroll} className='flex-1 overflow-y-auto'>
					<MDXEditor
						key='original'
						markdown={original}
						readOnly
						contentEditableClassName='prose max-w-none px-10 py-20 bg-base-50 focus:outline-none'
						plugins={PLUGINS}
					/>
				</div>

				{/* Divider */}
				<div className='w-px shrink-0 bg-base-300' />

				{/* Right — Proposal */}
				<div
					ref={rightRef}
					onScroll={handleRightScroll}
					className='flex-1 overflow-y-auto'
				>
					<MDXEditor
						key='proposal'
						markdown={proposal}
						readOnly
						contentEditableClassName='prose max-w-none px-10 py-20 bg-base-50 focus:outline-none'
						plugins={PLUGINS}
					/>
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
					className='cursor-pointer rounded-md bg-primary-100 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-800 active:opacity-80'
				>
					Aplicar Cambios
				</button>
			</div>
		</div>
	);
}
