'use client';

import { useEffect, useRef, useState } from 'react';
import type { ChatSessionSummary } from '@/entities/chat';
import { ChevronDown, Plus, Trash } from '@/shared/ui';
import { Ai } from '@/shared/ui';

interface SessionSelectorProps {
	title?: string;
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

const sessionLabel = (session: ChatSessionSummary | undefined) =>
	session?.title?.trim() || 'Nuevo chat';

export const SessionSelector = ({
	title = 'Agente IA',
	sessions,
	activeSessionId,
	loading,
	onSelect,
	onCreate,
	onDelete,
}: SessionSelectorProps) => {
	const [open, setOpen] = useState(false);
	const rootRef = useRef<HTMLDivElement>(null);

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
	const chatName = activeSessionId ? sessionLabel(activeSession) : null;

	return (
		<div
			ref={rootRef}
			className='relative flex items-center'
			onMouseEnter={() => setOpen(true)}
			onMouseLeave={() => setOpen(false)}
		>
			<button
				type='button'
				disabled={loading}
				aria-haspopup='listbox'
				aria-expanded={open}
				aria-label='Seleccionar chat'
				className='flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-neutral-0 transition-colors hover:bg-ai-600 cursor-pointer'
			>
				<Ai size={14} color='text-neutral-0' />
				{open && chatName ? (
					<>
						<span className='truncate text-xs font-semibold text-neutral-0 max-w-[140px] md:text-sm md:max-w-[200px]'>
							{chatName}
						</span>
						<span className='transition-transform rotate-180'>
							<ChevronDown size={12} color='text-neutral-0' />
						</span>
					</>
				) : (
					<h3 className='font-semibold text-neutral-0 text-xs md:text-sm'>{title}</h3>
				)}
			</button>

			{open && (
				<div
					role='listbox'
					aria-label='Chats'
					className='absolute left-0 top-full z-50 w-64 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-0 shadow-lg'
				>
					<div className='max-h-48 overflow-y-auto py-1'>
						<button
							type='button'
							onClick={() => {
								onCreate();
								setOpen(false);
							}}
							className='flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-ai-600 transition-colors hover:bg-ai-50 md:text-sm'
						>
							<Plus size={14} color='text-current' />
							Nuevo chat
						</button>

						{sessions.length > 0 && (
							<div className='border-t border-neutral-100' />
						)}

						{sessions.map((session, index) => (
							<div
								key={session.id}
								className={`flex items-center gap-1 pr-1.5 transition-colors ${
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
									className='flex min-w-0 flex-1 flex-col gap-0.5 px-3 py-1.5 text-left'
								>
									<span
										className={`truncate text-xs font-medium md:text-sm ${
											activeSessionId === session.id
												? 'text-ai-700'
												: 'text-neutral-700'
										}`}
									>
										{session.title?.trim() || `Chat ${index + 1}`}
									</span>
									<span className='text-[10px] text-neutral-400 md:text-xs'>
										{relativeTime(session.last_message_at ?? session.created_at)}
									</span>
								</button>
								<button
									type='button'
									onClick={() => onDelete(session.id)}
									title='Eliminar chat'
									aria-label={`Eliminar chat ${session.title?.trim() || index + 1}`}
									className='shrink-0 cursor-pointer rounded-lg p-1 text-neutral-400 transition-colors hover:bg-error-50 hover:text-error-500'
								>
									<Trash size={14} color='text-current' />
								</button>
							</div>
						))}

						{sessions.length === 0 && (
							<p className='px-3 py-1.5 text-xs text-neutral-400'>
								Aún no hay otros chats.
							</p>
						)}
					</div>
				</div>
			)}
		</div>
	);
};
