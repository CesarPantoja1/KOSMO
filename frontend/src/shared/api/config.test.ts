import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadConfig() {
	vi.resetModules();
	return import('./config');
}

afterEach(() => {
	vi.unstubAllEnvs();
});

describe('API_BASE_URL', () => {
	it('uses the current origin in production when no public API URL is baked into the image', async () => {
		vi.stubEnv('NODE_ENV', 'production');
		vi.stubEnv('NEXT_PUBLIC_API_URL', '');

		const { API_BASE_URL } = await loadConfig();

		expect(API_BASE_URL).toBe('');
	});

	it('keeps an explicitly configured API URL', async () => {
		vi.stubEnv('NODE_ENV', 'production');
		vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example.test');

		const { API_BASE_URL } = await loadConfig();

		expect(API_BASE_URL).toBe('https://api.example.test');
	});
});
