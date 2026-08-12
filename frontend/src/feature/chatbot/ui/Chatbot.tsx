'use client';

import { Ai, Close, Send } from '@/shared/ui';
import { useEffect, useRef, useState } from 'react';
import type { ChangeSuggestion, ChatMessage } from '../types/chatbot';
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
	/** Callback emitido cuando el usuario interactúa con una sugerencia de cambio.
	 *  La página consumidora decide qué hacer con la acción. */
	onPlanAction?: (
		action: 'add' | 'remove' | 'discard',
		suggestion: ChangeSuggestion,
		messageId: string,
	) => void;
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
	onPlanAction,
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
		<div className='flex h-full w-full flex-col overflow-hidden bg-base-50'>
			{/* Header */}
			<header className='flex items-center justify-between border-b border-stone-300 bg-ai px-5 py-4'>
				<div className='flex items-center gap-2'>
					<Ai size={20} color='text-base-50' />
					<div>
						<h3 className='font-semibold text-base-50'>{title}</h3>
						<p className='text-xs text-base-100'>{subtitle}</p>
					</div>
				</div>
				<button
					type='button'
					onClick={onClose}
					className='rounded cursor-pointer p-1 text-base-50'
				>
					<Close color='' />
				</button>
			</header>

			{/* Mensajes */}
			<div className='flex-1 overflow-y-auto space-y-4 px-5 py-5'>
				{messages.length === 0 && !isLoading && (
					<div className='flex items-start gap-3'>
						<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai'>
							<Ai size={16} color='text-base-50' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
							<p className='text-sm leading-6 text-stone-700'>{greeting}</p>
						</div>
					</div>
				)}

				{messages.map((message) => (
					<ChatbotMessage
						key={message.id}
						message={message}
						onPlanAction={onPlanAction}
					/>
				))}

				{(isSending || isLoading) && (
					<div className='flex items-start gap-3'>
						<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai'>
							<Ai size={16} color='text-base-50' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
							<span className='flex items-center gap-1 text-sm text-stone-500'>
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
			<div className='border-t border-stone-200 bg-white p-3'>
				<div className='flex items-end gap-2 rounded-2xl border border-stone-300 bg-base-50 px-3 py-2 transition-colors focus-within:border-ai'>
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
						className='
				max-h-36
				min-h-[24px]
				flex-1
				resize-none
				bg-transparent
				py-1
				text-sm
				leading-6
				outline-none
			'
					/>

					<button
						type='button'
						onClick={handleSend}
						disabled={!canSend}
						className='btn btn-ai rounded-full'
					>
						<Send size={16} color='' />
					</button>
				</div>

				<p className='mt-2 px-1 text-[11px] text-stone-400'>
					Enter para enviar • Shift + Enter para nueva línea
				</p>
			</div>
		</div>
	);
};
