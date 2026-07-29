export interface DiscoveryResponse {
	id: string;
	project_id: string;
	content: string;
}

export interface DiscoveryChatResponse {
	id: string;
	role: string;
	content: string;
	create_at: string;
	change_suggestion?: {
		section: string;
		diff_before: string;
		diff_after: string;
		rationale: string;
	} | null;
}
