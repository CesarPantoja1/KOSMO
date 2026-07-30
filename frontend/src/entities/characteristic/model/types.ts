export interface CharacteristicResponse {
	id: string;
	project_id: string;
	number: number;
	title: string;
	slug: string;
	description: string;
	origin: string;
	display_id: string;
}

export interface SuggestCharacteristic {
	number: number;
	title: string;
	description: string;
	origin: string;
}

export interface CharacteristicSave {
	title: string;
	description: string;
	rationale: string;
}

export interface CharacteristicChatResponse {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
	change_suggestion?: {
		id: string;
		section: string;
		description: string;
		diff_before: string;
		diff_after: string;
		rationale: string;
	} | null;
}
