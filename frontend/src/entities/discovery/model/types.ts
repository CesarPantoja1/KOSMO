export interface DiscoveryResponse {
	id: string;
	project_id: string;
	content: string;
}

export interface DiscoveryChatResponse {
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
