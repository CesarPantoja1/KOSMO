'use client';

import { useEffect, useRef, useState } from 'react';
import { Ai, Close } from '@/shared/ui';
import type { Message } from '../types/chatbot';
import { ChatbotMessage } from './chatbot-message';

interface Props {
	placeholder?: string;
	onClose?: () => void;
	messages?: Message[];
	onSendMessage?: (content: string) => Promise<void>;
	isLoading?: boolean;
}

export const Chatbot = ({
	onClose,
	placeholder = 'Escribe un mensaje...',
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

	return (
		<div className='flex h-full w-full flex-col overflow-hidden bg-base-50'>
			{/* Header */}
			<header className='flex items-center justify-between border-b border-stone-300 bg-ai px-5 py-4'>
				<div className='flex items-center gap-2'>
					<Ai size={20} color='text-base-50' />
					<div>
						<h3 className='font-semibold text-base-50'>Agente de descubrimiento</h3>
						<p className='text-xs text-base-100'>Asistente IA</p>
					</div>
				</div>

				<button type='button' onClick={onClose} className='rounded p-1 hover:bg-white/10'>
					<Close color='text-base-50' />
				</button>
			</header>

			{/* Mensajes */}
			<div className='flex-1 overflow-y-auto px-5 py-5 space-y-4'>
				{messages.length === 0 && !isLoading && (
					<div className='flex items-start gap-3'>
						<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai'>
							<Ai size={16} color='text-base-50' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
							<p className='text-sm leading-6 text-stone-700'>
								Hola 👋. ¿En qué puedo ayudarte con el descubrimiento del proyecto?
							</p>
						</div>
					</div>
				)}

				{messages.map((message) => (
					<ChatbotMessage key={message.id} message={message} />
				))}

				{(isSending || isLoading) && (
					<div className='flex items-start gap-3'>
						<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai'>
							<Ai size={16} color='text-base-50' />
						</div>
						<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
							<span className='flex gap-1 items-center text-sm text-stone-500'>
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
			<div className='border-t border-stone-300 bg-white p-4'>
				<div className='rounded-xl border border-stone-300 bg-base-50 p-3 transition-all focus-within:border-ai'>
					<textarea
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={placeholder}
						rows={3}
						disabled={isSending || isLoading}
						className='w-full resize-none bg-transparent outline-none text-sm leading-6 max-h-40'
					/>

					<div className='mt-2 flex justify-end'>
						<button
							type='button'
							onClick={handleSend}
							disabled={!canSend}
							className='
								flex items-center gap-2
								rounded-lg bg-ai px-4 py-2
								text-sm font-medium text-base-50
								transition-colors hover:opacity-90
								disabled:cursor-not-allowed disabled:opacity-50
							'
						>
							<Ai size={16} color='text-base-50' />
							{isSending || isLoading ? 'Pensando...' : 'Enviar'}
						</button>
					</div>
				</div>
				<p className='mt-2 text-xs text-stone-400'>Intro para enviar · Shift+Intro para nueva línea</p>
			</div>
		</div>
	);
};
