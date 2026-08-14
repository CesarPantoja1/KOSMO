export interface Change {
	applied: boolean;
	change_description: string;
	before: string;
	after: string;
}

export interface Modification {
	modified_document: string;
	modified_section: string;
	changes: Change[];
	undo_version_id: string;
	clarification_message: string;
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
	modification: Modification | null;
	redirect: {
		target_phase: string;
		redirect_message: string;
	} | null;
	consistency: {
		phase: string;
		artifact_id: string;
		artifact_type: string;
		artifact_label: string;
		section: string;
		rationale: string;
		diff_suggestion: {};
	} | null;
}
