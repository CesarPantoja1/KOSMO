import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';
import type {
	ChatPhase,
	ChatSessionListResponse,
	ChatSessionSummary,
	CreateChatSessionResponse,
} from '../model/types';

const mockSessions: ChatSessionSummary[] = [];

export async function listChatSessions(
	projectId: string,
	phase: ChatPhase,
	contextId: string | null,
): Promise<ChatSessionSummary[]> {
	if (USE_MOCKS) {
		return [...mockSessions];
	}
	const query = new URLSearchParams({ phase });
	if (contextId) query.set('context_id', contextId);
	const data = await apiClient<ChatSessionListResponse>(
		`/api/v1/projects/${projectId}/chat-sessions?${query.toString()}`,
		{ method: 'GET' },
	);
	return data.sessions;
}

export async function deleteChatSession(
	projectId: string,
	sessionId: string,
): Promise<void> {
	if (USE_MOCKS) {
		const index = mockSessions.findIndex((s) => s.id === sessionId);
		if (index >= 0) mockSessions.splice(index, 1);
		return;
	}
	await apiClient<void>(
		`/api/v1/projects/${projectId}/chat-sessions/${sessionId}`,
		{ method: 'DELETE' },
	);
}

export async function createChatSession(
	projectId: string,
	phase: ChatPhase,
	contextId: string | null,
): Promise<CreateChatSessionResponse> {
	if (USE_MOCKS) {
		const session: CreateChatSessionResponse = {
			id: crypto.randomUUID(),
			session_id: crypto.randomUUID(),
			phase,
			context_id: contextId,
			created_at: new Date().toISOString(),
			message_count: 0,
			last_message_at: null,
			title: '',
		};
		mockSessions.unshift(session);
		return session;
	}
	return apiClient<CreateChatSessionResponse>(
		`/api/v1/projects/${projectId}/chat-sessions`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ phase, context_id: contextId }),
		},
	);
}
