'use client';

import { Ai, Close, Send } from '@/shared/ui';
import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/chatbot';
import { ChatbotMessage } from './chatbot-message';

interface Props {
	/** Titulo del agente mostrado en el header */
	title?: string;
	/** Subtítulo del agente mostrado en el header */
	subtitle?: string;
	/** Mensaje de bienvenida cuando no hay historial */
	greeting?: string;
	placeholder?: string;
	onClose?: () => void;
	messages?: ChatMessage[];
	onSendMessage?: (content: string) => Promise<void>;
	isLoading?: boolean;
}

export const Chatbot = ({
	title = 'Agente IA',
	subtitle = 'Asistente IA',
	greeting = 'Hola 👋. ¿En qué puedo ayudarte?',
	placeholder = 'Escribe un mensaje...',
	onClose,
	messages = [],
	onSendMessage,
	isLoading = false,
}: Props) => {
	const [input, setInput] = useState('');
	const [isSending, setIsSending] = useState(false);
	const messagesEndRef = useRef<HTMLDivElement>(null);

	const canSend = input.trim().length > 0 && !isSending && !isLoading;

	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	}, [messages, isLoading]);

	const handleSend = async () => {
		const trimmed = input.trim();
		if (!trimmed || !onSendMessage) return;
		setInput('');
		setIsSending(true);
		try {
			await onSendMessage(trimmed);
		} catch (error) {
			console.error(error);
		} finally {
			setIsSending(false);
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	};

	// Ajusta la altura del textarea automáticamente según el contenido
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	useEffect(() => {
		const textarea = textareaRef.current;
		if (!textarea) return;

		textarea.style.height = '0px';
		textarea.style.height = `${textarea.scrollHeight}px`;
	}, [input]);

	return (
		<div className='flex h-full w-full flex-col overflow-hidden bg-neutral-0 border-l border-neutral-200'>
			{/* Header */}
			<header className='flex items-center justify-between border-b border-ai-600 bg-ai-500 px-5 py-4'>
				<div className='flex items-center gap-2'>
					<Ai size={18} color='text-neutral-0' />
					<div>
						<h3 className='font-semibold text-neutral-0 text-sm'>{title}</h3>
						<p className='text-xs text-ai-100'>{subtitle}</p>
					</div>
				</div>
				<button
					type='button'
					onClick={onClose}
					className='rounded-md cursor-pointer p-1 text-neutral-0 hover:bg-ai-600 transition-colors'
				>
					<Close color='' />
				</button>
			</header>

			{/* Mensajes */}
			<div className='flex-1 overflow-y-auto space-y-4 px-4 py-5 bg-neutral-50'>
				{messages.length === 0 && !isLoading && (
					<div className='flex items-start gap-3'>
						<div className='flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-500'>
							<Ai size={14} color='text-neutral-0' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-neutral-0 border border-neutral-200 px-4 py-3 shadow-sm'>
							<p className='text-sm leading-6 text-neutral-700'>{greeting}</p>
						</div>
					</div>
				)}

				{messages.map((message) => (
					<ChatbotMessage
						key={message.id}
						message={message}
					/>
				))}

				{(isSending || isLoading) && (
					<div className='flex items-start gap-3'>
						<div className='flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-500'>
							<Ai size={14} color='text-neutral-0' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-neutral-0 border border-neutral-200 px-4 py-3 shadow-sm'>
							<span className='flex items-center gap-1 text-sm text-neutral-400'>
								<span className='animate-bounce [animation-delay:0ms]'>·</span>
								<span className='animate-bounce [animation-delay:150ms]'>·</span>
								<span className='animate-bounce [animation-delay:300ms]'>·</span>
							</span>
						</div>
					</div>
				)}

				<div ref={messagesEndRef} />
			</div>

			{/* Input */}
			<div className='border-t border-neutral-200 bg-neutral-0 p-3'>
				<div className='flex items-end gap-2 rounded-xl border border-neutral-300 bg-neutral-50 px-3 py-2 transition-colors focus-within:border-ai-500 focus-within:ring-2 focus-within:ring-ai-500/15'>
					<textarea
						value={input}
						onChange={(e) => {
							setInput(e.target.value);
							e.target.style.height = '0px';
							e.target.style.height = `${e.target.scrollHeight}px`;
						}}
						ref={textareaRef}
						onKeyDown={handleKeyDown}
						placeholder={placeholder}
						rows={1}
						disabled={isSending || isLoading}
						className='max-h-36 min-h-[24px] flex-1 resize-none bg-transparent py-1 text-sm leading-6 outline-none text-neutral-800 placeholder:text-neutral-400'
					/>
					<button
						type='button'
						onClick={handleSend}
						disabled={!canSend}
						className='btn btn-ai rounded-full p-2'
					>
						<Send size={15} color='' />
					</button>
				</div>
				<p className='mt-2 px-1 text-[11px] text-neutral-400'>
					Enter para enviar • Shift + Enter para nueva línea
				</p>
			</div>
		</div>
	);
};
