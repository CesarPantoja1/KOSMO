export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChangeSuggestion {
	id: string;
	section: string;
	description: string;
	diff_before: string;
	diff_after: string;
	rationale: string | null;
	applied: boolean;
	not_applied_reason: string | null;
}

export interface ModificationResult {
	applied: boolean;
	modified_section: string | null;
	change_description: string | null;
	modified_document: string | null;
	before: string | null;
	after: string | null;
	undo_version_id: string | null;
	clarification_message: string | null;
}

export interface RedirectInfo {
	target_phase: string;
	redirect_message: string;
}

export interface ChatMessage {
	id: string;
	role: ChatRole;
	content: string;
	created_at: string;
	change_suggestions: ChangeSuggestion[] | null;
	modification: ModificationResult | null;
}

export interface ChatResponse {
	message: ChatMessage;
	modification: ModificationResult | null;
	redirect: RedirectInfo | null;
	consistency: Record<string, unknown>[] | null;
}

export interface ChatHistory {
	phase: string;
	context: string;
	messages: ChatMessage[];
	has_more: boolean;
	next_cursor: string | null;
}

export type ChatPhase = 'discovery' | 'features' | 'requirements' | 'model';

export interface ChatSessionSummary {
	id: string;
	phase: ChatPhase;
	context_id: string | null;
	created_at: string;
	message_count: number;
	last_message_at: string | null;
	title: string;
}

export interface CreateChatSessionRequest {
	phase: ChatPhase;
	context_id: string | null;
}

export interface CreateChatSessionResponse extends ChatSessionSummary {
	session_id: string;
}

export interface ChatSessionListResponse {
	sessions: ChatSessionSummary[];
}
