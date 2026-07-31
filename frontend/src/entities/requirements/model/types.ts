export interface RequirementsResponse {
	feature_id: string;
	feature_number: number;
	requirements_markdown: string;
	total: number;
}

export interface RequirementChatResponse {
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
	is_invalid_format?: boolean;
}

