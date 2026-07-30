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
						max-w-[85%] px-4 py-3 text-sm leading-6
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

			{message.change_suggestion &&
				(message.change_suggestion.diff_before ||
					message.change_suggestion.diff_after) && (
					<div className='w-full'>
						<TarjetaRecepcionPlan
							suggestion={message.change_suggestion}
							onAction={(action) =>
								onPlanAction?.(action, message.change_suggestion!, message.id)
							}
						/>
					</div>
				)}
		</div>
	);
};
