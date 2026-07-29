export interface ChangeSuggestion {
	section: string;
	diff_before: string;
	diff_after: string;
	rationale: string | null;
}

export interface Message {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: number;
	change_suggestion?: ChangeSuggestion;
}
