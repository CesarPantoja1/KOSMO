export interface RequirementsResponse {
	feature_id: string;
	feature_number: number;
	document_markdown: string;
	total: number;
}

export interface RequirementChatResponse {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
	change_suggestions?: Array<{
		id: string;
		section: string;
		description: string;
		diff_before: string;
		diff_after: string;
		rationale: string;
	}> | null;
	is_invalid_format?: boolean;
}

