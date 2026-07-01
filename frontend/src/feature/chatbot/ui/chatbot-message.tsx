'use client';

import type { Message } from '../types/chatbot';

interface ChatbotMessageProps {
	message: Message;
}

export const ChatbotMessage = ({ message }: ChatbotMessageProps) => {
	// TODO: implementar burbuja de mensaje
	return <div>{message.content}</div>;
};
