import type { Message } from '../types/chatbot';

export async function sendMessage(messages: Message[]): Promise<string> {
	const response = await fetch('/api/chatbot', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ messages }),
	});
	if (!response.ok) throw new Error('Error al enviar mensaje');
	const data = await response.json();
	return data.reply;
}
