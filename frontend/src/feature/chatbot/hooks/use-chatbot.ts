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
	const [messages, setMessages] = useState<Message[]>([
		{
			id: 'msg_01',
			role: 'assistant',
			content: 'He analizado tus requerimientos y te sugiero el siguiente cambio para alinear la sección con el alcance de LATAM.',
			timestamp: 1716301200000,
			change_suggestion: {
				section: '2 Alcance del producto',
				diff_before: 'El producto está limitado al mercado de Ecuador y no incluye soporte multi-moneda.',
				diff_after: 'El alcance del producto se extiende a toda la región LATAM, incluyendo soporte para múltiples monedas y configuraciones regionales.',
				rationale: 'Para cumplir con la visión B2B expansiva.'
			}
		}
	]);
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
