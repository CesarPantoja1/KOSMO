'use client';

import { useEffect, useRef, useState } from 'react';
import type { ChatSessionSummary } from '@/entities/chat';
import { ChevronDown, Plus, Trash } from '@/shared/ui';

interface SessionSelectorProps {
	sessions: ChatSessionSummary[];
	activeSessionId: string | null;
	loading: boolean;
	onSelect: (sessionId: string | null) => void;
	onCreate: () => void;
	onDelete: (sessionId: string) => void;
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

const sessionLabel = (session: ChatSessionSummary | undefined) =>
	session?.title?.trim() || 'Nuevo chat';

export const SessionSelector = ({
	sessions,
	activeSessionId,
	loading,
	onSelect,
	onCreate,
	onDelete,
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

	const activeSession = activeSessionId
		? sessions.find((s) => s.id === activeSessionId)
		: undefined;
	const triggerLabel = activeSessionId ? sessionLabel(activeSession) : 'Chat actual';

	return (
		<div
			ref={rootRef}
			className='flex items-center gap-2 border-b border-neutral-200 bg-neutral-0 px-4 py-2'
		>
			<div className='relative flex-1'>
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
					<span className={`transition-transform ${open ? 'rotate-180' : ''}`}>
						<ChevronDown size={14} color='text-neutral-400' />
					</span>
				</button>

				{open && (
					<div
						role='listbox'
						aria-label='Chats'
						className='absolute left-0 right-0 top-full z-10 mt-1 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-0 shadow-lg'
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
								<div
									key={session.id}
									className={`flex items-center gap-1 pr-2 transition-colors ${
										activeSessionId === session.id ? 'bg-ai-50' : 'hover:bg-neutral-50'
									}`}
								>
									<button
										type='button'
										role='option'
										aria-selected={activeSessionId === session.id}
										onClick={() => {
											onSelect(session.id);
											setOpen(false);
										}}
										className='flex min-w-0 flex-1 flex-col gap-0.5 px-3 py-2 text-left'
									>
										<span
											className={`truncate text-sm font-medium ${
												activeSessionId === session.id
													? 'text-ai-700'
													: 'text-neutral-700'
											}`}
										>
											{session.title?.trim() || `Chat ${index + 1}`}
										</span>
										<span className='text-xs text-neutral-400'>
											{relativeTime(session.last_message_at ?? session.created_at)}
										</span>
									</button>
									<button
										type='button'
										onClick={() => onDelete(session.id)}
										title='Eliminar chat'
										aria-label={`Eliminar chat ${session.title?.trim() || index + 1}`}
										className='shrink-0 cursor-pointer rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-error-50 hover:text-error-500'
									>
										<Trash size={16} color='text-current' />
									</button>
								</div>
							))}

							{sessions.length === 0 && (
								<p className='px-3 py-2 text-sm text-neutral-400'>
									Aún no hay otros chats.
								</p>
							)}
						</div>
					</div>
				)}
			</div>

			<button
				type='button'
				onClick={onCreate}
				disabled={loading}
				aria-label='Nuevo chat'
				title='Nuevo chat'
				className='flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-neutral-300 bg-neutral-0 text-neutral-600 transition-colors hover:border-ai-500 hover:text-ai-600 focus:border-ai-500 focus:outline-none disabled:opacity-60'
			>
				<Plus size={16} color='text-current' />
			</button>
		</div>
	);
};
