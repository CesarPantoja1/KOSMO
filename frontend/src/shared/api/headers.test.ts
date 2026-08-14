import { describe, expect, it, beforeEach } from 'vitest';
import { useAuthStore } from '../store/auth.store';
import { authHeaders } from './headers';

describe('authHeaders', () => {
	beforeEach(() => {
		useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, mockUserId: null });
		delete process.env.NEXT_PUBLIC_AUTH_DISABLED;
	});

	it('usa X-Mock-User cuando la auth está deshabilitada', () => {
		process.env.NEXT_PUBLIC_AUTH_DISABLED = 'true';
		useAuthStore.setState({ mockUserId: 'usr_test' });

		const headers = authHeaders();

		expect(headers.get('X-Mock-User')).toBe('usr_test');
		expect(headers.has('Authorization')).toBe(false);
	});

	it('usa Authorization Bearer con el token del store', () => {
		process.env.NEXT_PUBLIC_AUTH_DISABLED = 'false';
		useAuthStore.setState({ accessToken: 'token-123' });

		const headers = authHeaders();

		expect(headers.get('Authorization')).toBe('Bearer token-123');
		expect(headers.has('X-Mock-User')).toBe(false);
	});

	it('no agrega header de auth si no hay token ni mock', () => {
		process.env.NEXT_PUBLIC_AUTH_DISABLED = 'false';

		const headers = authHeaders();

		expect(headers.has('Authorization')).toBe(false);
		expect(headers.has('X-Mock-User')).toBe(false);
	});

	it('conserva los headers existentes y no sobrescribe el auth', () => {
		process.env.NEXT_PUBLIC_AUTH_DISABLED = 'false';
		useAuthStore.setState({ accessToken: 'token-123' });

		const headers = authHeaders({ 'Content-Type': 'application/json', Authorization: 'Bearer custom' });

		expect(headers.get('Authorization')).toBe('Bearer custom');
		expect(headers.get('Content-Type')).toBe('application/json');
	});
});
