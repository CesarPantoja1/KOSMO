import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();

function mockFetchOk(body: unknown) {
	fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => body });
}

function mockFetchError(status: number, body: unknown) {
	fetchMock.mockResolvedValue({
		ok: false,
		status,
		headers: new Headers(),
		json: async () => body,
	});
}

afterEach(() => {
	fetchMock.mockReset();
	vi.unstubAllGlobals();
	vi.resetModules();
	vi.doUnmock('@/shared/api/config');
});

describe('chat/api — modo real (USE_MOCKS=false)', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
	});

	it('listChatSessions agrega phase y context_id como query params', async () => {
		// Arrange
		const { listChatSessions } = await import('./api');
		mockFetchOk({ sessions: [{ id: 's1' }] });

		// Act
		const result = await listChatSessions('prj_01', 'discovery', 'ctx_1');

		// Assert
		expect(result).toHaveLength(1);
		const [url] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/projects/prj_01/chat-sessions');
		expect(url).toContain('phase=discovery');
		expect(url).toContain('context_id=ctx_1');
	});

	it('listChatSessions omite context_id cuando es null', async () => {
		// Arrange
		const { listChatSessions } = await import('./api');
		mockFetchOk({ sessions: [] });

		// Act
		await listChatSessions('prj_01', 'discovery', null);

		// Assert
		const [url] = fetchMock.mock.calls[0];
		expect(url).not.toContain('context_id');
	});

	it('deleteChatSession hace DELETE a la sesión', async () => {
		// Arrange
		const { deleteChatSession } = await import('./api');
		mockFetchOk(null);

		// Act
		await deleteChatSession('prj_01', 'sess_1');

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/projects/prj_01/chat-sessions/sess_1'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('createChatSession hace POST con phase y context_id', async () => {
		// Arrange
		const { createChatSession } = await import('./api');
		mockFetchOk({ id: 's1', session_id: 's1', phase: 'discovery', context_id: null });

		// Act
		await createChatSession('prj_01', 'discovery', null);

		// Assert
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/projects/prj_01/chat-sessions');
		expect(JSON.parse((options as RequestInit).body as string)).toEqual({
			phase: 'discovery',
			context_id: null,
		});
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		const { listChatSessions } = await import('./api');
		mockFetchError(500, { detail: 'Error interno' });

		// Act & Assert
		await expect(listChatSessions('prj_01', 'discovery', null)).rejects.toThrow(
			'Error interno',
		);
	});
});

describe('chat/api — modo mock (USE_MOCKS=true)', () => {
	beforeEach(() => {
		vi.resetModules();
		vi.doMock('@/shared/api/config', () => ({ USE_MOCKS: true }));
	});

	it('createChatSession agrega la sesión al store mock y listChatSessions la refleja', async () => {
		// Arrange
		const { createChatSession, listChatSessions } = await import('./api');

		// Act
		const created = await createChatSession('prj_01', 'discovery', 'ctx_1');
		const sessions = await listChatSessions('prj_01', 'discovery', 'ctx_1');

		// Assert
		expect(created.phase).toBe('discovery');
		expect(sessions).toHaveLength(1);
		expect(sessions[0].id).toBe(created.id);
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it('deleteChatSession elimina la sesión del store mock', async () => {
		// Arrange
		const { createChatSession, listChatSessions, deleteChatSession } = await import('./api');
		const created = await createChatSession('prj_01', 'discovery', null);

		// Act
		await deleteChatSession('prj_01', created.id);
		const sessions = await listChatSessions('prj_01', 'discovery', null);

		// Assert
		expect(sessions.find((s) => s.id === created.id)).toBeUndefined();
	});
});
