'use client';

import type { Message } from '../types/chatbot';
import { TarjetaRecepcionPlan } from './TarjetaRecepcionPlan';

interface ChatbotMessageProps {
	message: Message;
}

export const ChatbotMessage = ({ message }: ChatbotMessageProps) => {
	// TODO: implementar burbuja de mensaje y estilos según role
	return (
		<div className="flex flex-col mb-4">
			<div>{message.content}</div>
			{message.change_suggestion && (
				<TarjetaRecepcionPlan suggestion={message.change_suggestion} />
			)}
		</div>
	);
};
