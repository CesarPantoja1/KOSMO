import type { ChatMessage } from './types';

export function createUserMessage(content: string): ChatMessage {
	return {
		id: crypto.randomUUID(),
		role: 'user',
		content,
		created_at: new Date().toISOString(),
		change_suggestions: null,
		modification: null,
	};
}

export function createAssistantError(content: string): ChatMessage {
	return {
		id: crypto.randomUUID(),
		role: 'assistant',
		content,
		created_at: new Date().toISOString(),
		change_suggestions: null,
		modification: null,
	};
}

export function appendMessage(messages: ChatMessage[], message: ChatMessage): ChatMessage[] {
	return [...messages, message];
}
