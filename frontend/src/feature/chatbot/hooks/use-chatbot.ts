'use client';

import { useState, useCallback } from 'react';
import type { Message } from '../types/chatbot';
import { sendMessage } from '../api/chatbot-api';

interface UseChatbotReturn {
	messages: Message[];
	isLoading: boolean;
	error: string | null;
	send: (content: string) => Promise<void>;
	clear: () => void;
}

export function useChatbot(): UseChatbotReturn {
	const [messages, setMessages] = useState<Message[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const send = useCallback(async (content: string) => {
		// TODO: implement
	}, []);

	const clear = useCallback(() => {
		setMessages([]);
		setError(null);
	}, []);

	return { messages, isLoading, error, send, clear };
}
