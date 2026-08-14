'use client';

import { Ai } from '@/shared/ui';
import { MarkdownText } from '@/shared/ui/markdown-text';
import { TarjetaRecepcionPlan } from './TarjetaRecepcionPlan';
import { ChatMessage } from '@/entities/chat';

interface ChatbotMessageProps {
	message: ChatMessage;
}

export const ChatbotMessage = ({ message }: ChatbotMessageProps) => {
	const isUser = message.role === 'user';

	return (
		<div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
			<div
				className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
			>
				{!isUser && (
					<div className='flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-500'>
						<Ai size={14} color='text-neutral-0' />
					</div>
				)}
				<div
					className={`
						max-w-[85%] px-4 py-2.5 text-sm leading-6 wrap-break-word whitespace-pre-wrap
						${
							isUser
								? 'rounded-2xl rounded-br-sm bg-ai-500 text-neutral-0'
								: 'rounded-2xl rounded-tl-sm bg-neutral-0 border border-neutral-200 text-neutral-700 shadow-sm'
						}
					`}
				>
					{isUser ? message.content : <MarkdownText content={message.content} />}
				</div>
			</div>

			{message.change_suggestions &&
				message.change_suggestions.length > 0 &&
				message.change_suggestions.map((suggestion) => (
					<div className='w-full' key={suggestion.id}>
						<TarjetaRecepcionPlan suggestion={suggestion} />
					</div>
				))}
		</div>
	);
};
