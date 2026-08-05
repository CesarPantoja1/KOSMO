/**
 * Tipos propios del feature/chatbot.
 * Completamente agnósticos — no importan nada de entities/.
 * La página consumidora es responsable de adaptar sus tipos de dominio a estos.
 */

export interface ChangeSuggestion {
	id: string;
	section: string;
	description: string;
	diff_before: string;
	diff_after: string;
	rationale: string;
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
	change_suggestions?: ChangeSuggestion[] | null;
}
