'use client';

import { Ai } from '@/shared/ui';
import { MarkdownText } from '@/shared/ui/markdown-text';
import type { ChangeSuggestion, ChatMessage } from '../types/chatbot';
import { TarjetaRecepcionPlan } from './TarjetaRecepcionPlan';

interface ChatbotMessageProps {
	message: ChatMessage;
	onPlanAction?: (
		action: 'add' | 'remove' | 'discard',
		suggestion: ChangeSuggestion,
		messageId: string,
	) => void;
}

export const ChatbotMessage = ({ message, onPlanAction }: ChatbotMessageProps) => {
	const isUser = message.role === 'user';

	return (
		<div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
			<div
				className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
			>
				{!isUser && (
					<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai'>
						<Ai size={16} color='text-base-50' />
					</div>
				)}
				<div
					className={`
						max-w-[85%] px-5 py-2.5 text-sm leading-6 wrap-break-word whitespace-pre-wrap
						${
							isUser
								? 'rounded-2xl rounded-br-sm bg-ai text-base-50'
								: 'rounded-2xl rounded-tl-sm bg-stone-100 text-stone-700'
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
						<TarjetaRecepcionPlan
							messageId={message.id}
							suggestion={suggestion}
							onAction={(action) => onPlanAction?.(action, suggestion, message.id)}
						/>
					</div>
				))}
		</div>
	);
};
