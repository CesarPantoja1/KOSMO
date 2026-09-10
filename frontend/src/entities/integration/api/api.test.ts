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

describe('integration/api — modo real (USE_MOCKS=false)', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
	});

	it('getIntegrationStatus consulta el endpoint del proveedor', async () => {
		// Arrange
		const { getIntegrationStatus } = await import('./api');
		mockFetchOk({ provider: 'github', is_connected: true });

		// Act
		const result = await getIntegrationStatus('github');

		// Assert
		expect(result.is_connected).toBe(true);
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/integrations/github/status'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('connectIntegration hace POST con el código y redirect_uri', async () => {
		// Arrange
		const { connectIntegration } = await import('./api');
		mockFetchOk({ provider: 'github', is_connected: true, username: 'octocat' });

		// Act
		await connectIntegration('github', { code: 'abc', redirect_uri: 'https://app/perfil' });

		// Assert
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/integrations/github/connect');
		expect((options as RequestInit).method).toBe('POST');
		expect(JSON.parse((options as RequestInit).body as string)).toEqual({
			code: 'abc',
			redirect_uri: 'https://app/perfil',
		});
	});

	it('disconnectIntegration hace DELETE al endpoint del proveedor', async () => {
		// Arrange
		const { disconnectIntegration } = await import('./api');
		mockFetchOk(null);

		// Act
		await disconnectIntegration('railway');

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/integrations/railway'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		const { getIntegrationStatus } = await import('./api');
		mockFetchError(401, { error: 'invalid_grant', error_description: 'Credenciales inválidas' });

		// Act & Assert
		await expect(getIntegrationStatus('github')).rejects.toThrow();
	});
});

describe('integration/api — modo mock (USE_MOCKS=true)', () => {
	beforeEach(() => {
		vi.resetModules();
		vi.doMock('@/shared/api/config', () => ({ USE_MOCKS: true }));
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('getIntegrationStatus resuelve el estado mock conectado', async () => {
		// Arrange
		const { getIntegrationStatus } = await import('./api');

		// Act
		const promise = getIntegrationStatus('github');
		await vi.advanceTimersByTimeAsync(400);
		const result = await promise;

		// Assert
		expect(result.is_connected).toBe(true);
		expect(fetchMock).not.toHaveBeenCalled();
	});

	it('connectIntegration marca el proveedor como conectado', async () => {
		// Arrange
		const { connectIntegration } = await import('./api');

		// Act
		const promise = connectIntegration('github', { code: 'abc', redirect_uri: 'x' });
		await vi.advanceTimersByTimeAsync(800);
		const result = await promise;

		// Assert
		expect(result.is_connected).toBe(true);
		expect(result.username).toBe('mock-user');
	});

	it('disconnectIntegration marca el proveedor como desconectado', async () => {
		// Arrange
		const { getIntegrationStatus, disconnectIntegration } = await import('./api');

		// Act
		const disconnectPromise = disconnectIntegration('github');
		await vi.advanceTimersByTimeAsync(600);
		await disconnectPromise;

		const statusPromise = getIntegrationStatus('github');
		await vi.advanceTimersByTimeAsync(400);
		const status = await statusPromise;

		// Assert
		expect(status.is_connected).toBe(false);
	});
});
