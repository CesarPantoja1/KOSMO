import { describe, expect, it } from 'vitest';
import { buildGitHubAuthUrl, buildRailwayAuthUrl, DEFAULT_REDIRECT_URI } from './oauth-config';

describe('buildGitHubAuthUrl', () => {
	it('construye la URL de autorización de GitHub con el redirect_uri codificado', () => {
		// Act
		const url = buildGitHubAuthUrl(
			'https://app.example.com/perfil?x=1',
			'github.test-state',
			'pkce-challenge',
		);

		// Assert
		expect(url).toContain('https://github.com/login/oauth/authorize');
		expect(url).toContain('state=github.test-state');
		expect(url).toContain('redirect_uri=https%3A%2F%2Fapp.example.com%2Fperfil%3Fx%3D1');
		expect(url).toContain('code_challenge=pkce-challenge');
		expect(url).toContain('code_challenge_method=S256');
	});
});

describe('buildRailwayAuthUrl', () => {
	it('construye la URL de autorización de Railway con response_type y prompt=consent', () => {
		// Act
		const url = buildRailwayAuthUrl(
			'https://app.example.com/perfil',
			'railway.test-state',
			'pkce-challenge',
		);

		// Assert
		expect(url).toContain('https://backboard.railway.com/oauth/auth');
		expect(url).toContain('response_type=code');
		expect(url).toContain('state=railway.test-state');
		expect(url).toContain('prompt=consent');
		expect(url).toContain('redirect_uri=https%3A%2F%2Fapp.example.com%2Fperfil');
		expect(url).toContain('code_challenge=pkce-challenge');
	});
});

describe('DEFAULT_REDIRECT_URI', () => {
	it('apunta a la página de perfil sobre el dominio público configurado', () => {
		expect(DEFAULT_REDIRECT_URI).toContain('/perfil');
	});
});
