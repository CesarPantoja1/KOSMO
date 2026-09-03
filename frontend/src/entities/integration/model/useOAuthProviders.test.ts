import { describe, expect, it, vi } from 'vitest';

vi.mock('./useOAuthIntegration', () => ({
	useOAuthIntegration: vi.fn(() => ({ status: null })),
}));

import { useOAuthIntegration } from './useOAuthIntegration';
import { useGithubOAuth, useRailwayOAuth } from './useOAuthProviders';
import { DEFAULT_REDIRECT_URI } from './oauth-config';

const mockedHook = vi.mocked(useOAuthIntegration);

describe('useGithubOAuth', () => {
	it('invoca useOAuthIntegration con la configuración de GitHub', () => {
		// Act
		useGithubOAuth();

		// Assert
		expect(mockedHook).toHaveBeenCalledWith(
			expect.objectContaining({
				provider: 'github',
				label: 'GitHub',
				messageType: 'github-oauth-code',
				redirectUri: DEFAULT_REDIRECT_URI,
			}),
		);
	});

	it('permite sobreescribir el redirectUri', () => {
		// Act
		useGithubOAuth({ redirectUri: 'https://custom/perfil' });

		// Assert
		expect(mockedHook).toHaveBeenCalledWith(
			expect.objectContaining({ redirectUri: 'https://custom/perfil' }),
		);
	});
});

describe('useRailwayOAuth', () => {
	it('invoca useOAuthIntegration con la configuración de Railway', () => {
		// Act
		useRailwayOAuth();

		// Assert
		expect(mockedHook).toHaveBeenCalledWith(
			expect.objectContaining({
				provider: 'railway',
				label: 'Railway',
				messageType: 'railway-oauth-code',
				redirectUri: DEFAULT_REDIRECT_URI,
			}),
		);
	});
});
