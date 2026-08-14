'use client';

import { useEffect, useRef, useState } from 'react';
import type { ChatSessionSummary } from '@/entities/chat';
import { ArrowRight } from '@/shared/ui';

interface SessionSelectorProps {
	sessions: ChatSessionSummary[];
	activeSessionId: string | null;
	loading: boolean;
	onSelect: (sessionId: string | null) => void;
	onCreate: () => void;
}

function relativeTime(iso: string | null): string {
	if (!iso) return '';
	const diffMs = Date.now() - new Date(iso).getTime();
	const minutes = Math.max(1, Math.round(diffMs / 60_000));
	if (minutes < 60) return `hace ${minutes} min`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `hace ${hours} h`;
	return `hace ${Math.round(hours / 24)} d`;
}

const optionStyles = (isActive: boolean) =>
	`flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors ${
		isActive ? 'bg-ai-50' : 'hover:bg-neutral-50'
	}`;

export const SessionSelector = ({
	sessions,
	activeSessionId,
	loading,
	onSelect,
	onCreate,
}: SessionSelectorProps) => {
	const [open, setOpen] = useState(false);
	const rootRef = useRef<HTMLDivElement>(null);

	// Cierra el popover con clic fuera o Escape
	useEffect(() => {
		if (!open) return;
		const handlePointerDown = (e: MouseEvent) => {
			if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
				setOpen(false);
			}
		};
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Escape') setOpen(false);
		};
		document.addEventListener('mousedown', handlePointerDown);
		document.addEventListener('keydown', handleKeyDown);
		return () => {
			document.removeEventListener('mousedown', handlePointerDown);
			document.removeEventListener('keydown', handleKeyDown);
		};
	}, [open]);

	const activeIndex = activeSessionId
		? sessions.findIndex((s) => s.id === activeSessionId)
		: -1;
	const triggerLabel =
		activeIndex >= 0 ? `Chat ${activeIndex + 1}` : 'Chat actual';

	return (
		<div ref={rootRef} className='relative border-b border-neutral-200 bg-neutral-0 px-4 py-2'>
			<button
				type='button'
				onClick={() => setOpen((v) => !v)}
				disabled={loading}
				aria-haspopup='listbox'
				aria-expanded={open}
				aria-label='Seleccionar chat'
				className='flex h-9 w-full cursor-pointer items-center justify-between gap-2 rounded-lg border border-neutral-300 bg-neutral-0 px-3 text-sm text-neutral-700 transition-colors hover:border-ai-500 focus:border-ai-500 focus:outline-none disabled:opacity-60'
			>
				<span className='truncate font-medium'>{triggerLabel}</span>
				<span className={`transition-transform ${open ? 'rotate-90' : ''}`}>
					<ArrowRight size={14} color='text-neutral-400' />
				</span>
			</button>

			{open && (
				<div
					role='listbox'
					aria-label='Chats'
					className='absolute left-4 right-4 top-full z-10 mt-1 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-0 shadow-lg'
				>
					<div className='max-h-56 overflow-y-auto py-1'>
						<button
							type='button'
							role='option'
							aria-selected={activeSessionId === null}
							onClick={() => {
								onSelect(null);
								setOpen(false);
							}}
							className={optionStyles(activeSessionId === null)}
						>
							<span
								className={`text-sm font-medium ${
									activeSessionId === null ? 'text-ai-700' : 'text-neutral-700'
								}`}
							>
								Chat actual
							</span>
						</button>

						{sessions.map((session, index) => (
							<button
								key={session.id}
								type='button'
								role='option'
								aria-selected={activeSessionId === session.id}
								onClick={() => {
									onSelect(session.id);
									setOpen(false);
								}}
								className={optionStyles(activeSessionId === session.id)}
							>
								<span
									className={`text-sm font-medium ${
										activeSessionId === session.id
											? 'text-ai-700'
											: 'text-neutral-700'
									}`}
								>
									Chat {index + 1}
								</span>
								<span className='text-xs text-neutral-400'>
									{session.message_count} mensaje(s) ·{' '}
									{relativeTime(session.last_message_at ?? session.created_at)}
								</span>
							</button>
						))}

						{sessions.length === 0 && (
							<p className='px-3 py-2 text-sm text-neutral-400'>
								Aún no hay otros chats.
							</p>
						)}
					</div>

					<div className='border-t border-neutral-200 p-2'>
						<button
							type='button'
							onClick={() => {
								onCreate();
								setOpen(false);
							}}
							disabled={loading}
							className='btn btn-ai btn-sm w-full justify-center disabled:opacity-60'
						>
							+ Nuevo chat
						</button>
					</div>
				</div>
			)}
		</div>
	);
};
