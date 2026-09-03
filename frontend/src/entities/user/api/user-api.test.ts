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

beforeEach(() => {
	vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
	fetchMock.mockReset();
	vi.unstubAllGlobals();
});

describe('getUser', () => {
	it('consulta el endpoint /auth/me y devuelve el usuario', async () => {
		// Arrange
		const { getUser } = await import('./user-api');
		mockFetchOk({ subject: 'usr_1', name: 'Gian', email: 'g@example.com' });

		// Act
		const user = await getUser();

		// Assert
		expect(user.name).toBe('Gian');
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/auth/me'),
			expect.anything(),
		);
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		const { getUser } = await import('./user-api');
		mockFetchError(401, { error: 'invalid_grant', error_description: 'Sesión expirada' });

		// Act & Assert
		await expect(getUser()).rejects.toThrow();
	});
});
