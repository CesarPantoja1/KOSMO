import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { aiConfigApi } from './api';

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

describe('aiConfigApi', () => {
	it('getProviders consulta el catálogo de proveedores', async () => {
		// Arrange
		mockFetchOk([{ provider: 'openai', label: 'OpenAI' }]);

		// Act
		const result = await aiConfigApi.getProviders();

		// Assert
		expect(result).toHaveLength(1);
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/ai-config/providers'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('getConfig consulta la configuración actual', async () => {
		// Arrange
		mockFetchOk({ provider: 'openai', has_key: true });

		// Act
		const result = await aiConfigApi.getConfig();

		// Assert
		expect(result).toEqual({ provider: 'openai', has_key: true });
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/ai-config'),
			expect.objectContaining({ method: 'GET' }),
		);
	});

	it('saveConfig hace POST con los datos de configuración', async () => {
		// Arrange
		mockFetchOk({ provider: 'openai', has_key: true });

		// Act
		await aiConfigApi.saveConfig({ provider: 'openai', api_key: 'sk-123' } as never);

		// Assert
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/api/v1/ai-config');
		expect((options as RequestInit).method).toBe('POST');
		expect(JSON.parse((options as RequestInit).body as string)).toEqual({
			provider: 'openai',
			api_key: 'sk-123',
		});
	});

	it('deleteConfig hace DELETE de la configuración', async () => {
		// Arrange
		mockFetchOk(null);

		// Act
		await aiConfigApi.deleteConfig();

		// Assert
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/ai-config'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('testConnection hace POST con los datos de prueba', async () => {
		// Arrange
		mockFetchOk({ success: true });

		// Act
		const result = await aiConfigApi.testConnection({ provider: 'openai', api_key: 'sk-123' } as never);

		// Assert
		expect(result).toEqual({ success: true });
		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/ai-config/test'),
			expect.objectContaining({ method: 'POST' }),
		);
	});

	it('propaga el error de la API cuando la petición falla', async () => {
		// Arrange
		mockFetchError(422, {
			type: 'urn:kosmo:ai:auth-error',
			detail: 'Clave de API inválida',
		});

		// Act & Assert
		await expect(aiConfigApi.getConfig()).rejects.toThrow();
	});
});
